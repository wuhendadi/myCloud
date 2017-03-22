# -*- coding: utf-8 -*-

import os
import sys
import json
import types
import dbus
import gobject
import time
import ConfigParser
import cherrypy
import UtilFunc
import Error
import ProfileFunc
import thread
import threading
import StartFunc
import thumbnail
import Log
import WebFunc
from Sitelib import libandroidmod
from dbus.mainloop.glib import DBusGMainLoop
from PopoConfig import *
import PostStatic as static
import md5
from PopoConfig import MaxWidth, MaxHeight, MinWidth, MinHeight, filters
import CameraUtils
import mimetypes
from CameraFolderMonitorThread import CameraFolderMonitorThread

BUS_NAME        = "com.kortide.camera.camera_control_service"
BUS_PATH        = "/com/kortide/camera/camera_control_service"
BUS_INTERFACE   = "com.kortide.camera.camera_control_service.camera_service"
SAVE_PATH       = "CameraMonitor"
CAMERA_TYPE     = {"AUTO" : 0, "ANYKA_3918A1" : 1};
CONFIG_PATH     = "/popoCloudData/IpCamCtrl.ini"
RIGHT_REPORT    = "call successfully"
DBUS_NORLY      = "org.freedesktop.DBus.Error.NoReply"
CAMERA_INFO     = ["type","ip","uid", "deviceId", "alias","is_added","is_live","is_available",
                 "streams","media_stream_info"]
BIND_INFO       = ["type","uid", "deviceId", "mft","hw","ver","ip","alias","record","records","motiondetect",
                 "sensitive","interval","r1","r2","week","stream","islive","password"]
CAMERA_APP      = os.path.dirname(os.path.abspath(__file__)) + "/CameraCtrlService/camera-ctrl-service"
TIMEOUT         = 20
MAXMINUTES      = 24 * 60
MINMINUTES      = 0
SEND_ALARM_TIME = 20 * 60
DISK_ALARM_TIME = 12 * 60 * 60
KILL_CS_TIME    = 5 * 60
ALARM_TYPE      = type('Enum', (), {"CAMERA_ALARM": 1, "lOWSPACE_ALARM": 2, "FULLSPACE_ALARM": 3})
SPACE_TYPE      = type('Enum', (), {"LOW_SPACE": 500 * 1024, "FULL_SPACE": 100 * 1024})
ALARM_STATUS    = type('Enum', (), {"ALARM_ON": 1, "ALARM_OFF": 0})
SENSITIVE_INFO  = [1, 3, 5]
lock_serach     = threading.Lock()
cs_event        = threading.Event() #start camera service event
NEW_SNAP_SHORT_FILE_TIMEOUT = 5
#UtilFunc.setCmaeraFolder(SAVE_PATH)

def getProcessPID(str = None):
    if not str:
        return None
    pro_list = []
    str = str.split(" ")
    for _str in str:
        if _str:
            pro_list.append(_str)
    return pro_list[1]

def startCameraService():
    UtilFunc.getLogger().info("Start Camera-ctrl-Service!")
    s = libandroidmod.execute_shell("ps | grep "+ CAMERA_APP)
    if s : 
        os.system("busybox killall -9 camera-ctrl-service")
#        csPID = int(getProcessPID(s))
#        os.system("kill -9 %d"%csPID)
    os.system("chmod 777 "+ CAMERA_APP)
    os.system(CAMERA_APP+" /popoCloudData/cameraApp.ini &")
    time.sleep(2)    

def killCameraService():
    Log.info("Kill Camera-Ctrl-Service!")
    s = libandroidmod.execute_shell("ps | grep "+ CAMERA_APP)
    if s : 
        os.system("busybox killall -9 camera-ctrl-service")
#        print '**** s [%s]'%s
#        csPID = int(getProcessPID(s))
#        print csPID
#        os.system("kill -9 %d"%csPID)
    

class PubCameraCtrl:
    
    def __init__(self):
        DBusGMainLoop(set_as_default=True)
        self.parent           = ProfileFunc.getMainServer()
        self.cameras          = {}
        self.addingcameras    = []
        self.removeingcameras = []
        self.stream_id        = 0
        self.token            = 0
        self.alarmStatus      = 1
        self.msgs             = {}
        self.daystime         = 7
        self.killCstime       = time.time()
        self.alarmtime        = {}
        self.diskALarmTime    = {}
        self.search_list      = []
        self.emails           = []
        self.mobiles          = []
        self.alarminfo        = []
        self.dbus             = dbus.SessionBus()
        self.recordingCameras = []
        self.alarmRecording   = []
        self.alarmRecordTime  = {}
        self.newSnapShortFile = {}
        self.recModifyPwdResp = {}
        self.modifyPwdResult  = {}
        self.login            = {}
        self.modifyPwd        = {}
        self.scanFolder       = []
        self.stoped           = False
        self.recNewCamSuc     = False
        self.record_path      = None
        self.update_thread    = None
        self.reconnect_thread = None
        self.cameraFolderMonitor = None
        self._setScanFolder()
        self._initCameraDB()
        thread.start_new_thread(self._scanCameraFolder, ())
        thread.start_new_thread(self._checkWatchDog, ())
        thread.start_new_thread(self._recvStartCSEvent, ())
        self._initFileMonitor()
        self.initEventMethods()

    def initEventMethods(self):
        self.EventMethods = {
                             "add":self.Add,
                             "getInfo":self.GetInfo,
                             "list":self.List,
                             "remove":self.Remove,
                             "rename":self.Rename,
                             "setRecordConfig":self.SetRecordConfig,
                             "setInterval":self.SetInterval,
                             "setMobile":self.SetMobile,
                             "getMobiles":self.GetMobiles,
                             "setEmail":self.SetEmail,
                             "getEmails":self.GetEmails,
                             "setAlarmInfo":self.SetAlarmInfo,
                             "getAlarmInfo":self.GetAlarmInfo,
                             "setRegular":self.SetRegular,
                             "recordList":self.RecordsList,
                             "snapshot":self.Snapshot,
                             "record":self.Record,
                             "syncCameraInfo":self.SyncCameraInfo,
                             "modifyCamerapwd":self.ModifyCameraPwd,
                             "stream":self.playMedia,
                             "fileList":self.FileListfromDB,
                             "downloadThumb":self.DownloadThumb,
                             "album":self.GetAlbum
                             }

    def getEventMethods(self):
        keys =self.EventMethods.keys()
        return keys

    def dispatchEvent(self,  intent,args, param):
        ret = self.EventMethods.get(intent)(args, param)
        return ret

    def _initDbusSession(self):
        try:
            self.d_obj = self._getRmoteObject()
            self.iface = self._getInterFace()
            self._addAllSignalReceiver()
            self._startMessageLoop()
        except Exception, e:
            Log.error("_initDbusSession Failed! Reason[%s]"%e)
            return
        cs_event.set()
        
    def _startMessageLoop(self):
        gobject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus_loop = gobject.MainLoop()
        
        loopThread = threading.Thread(name="glib_mainloop",target=dbus_loop.run)
        loopThread.start()

    def _cameraWatch(self,flag=False):
        try:
            s = libandroidmod.execute_shell("ps | grep "+ CAMERA_APP)
            if s and not flag: return 
            else: raise
        except:
            Log.info("Camera-Ctrl-Service Haven't Existed! Start it!")
            startCameraService()
            self.killCstime = time.time()
            self._initDbusSession()
            
    def _startUpdateThread(self):
        if not self.update_thread:
            Log.info("***** start update thread ******")
            self.update_thread = StartFunc.StoppableThread(target=self._update, args=())
            self.update_thread.start()
    
    def _startReconnectCameraThread(self):
        if not self.reconnect_thread:
            Log.info("***** start Reconnect Camera thread ******")
            self.reconnect_thread = StartFunc.StoppableThread(target=self._reConnectCameraThread, args=())
            self.reconnect_thread.start()
            
    
    def _initRecordData(self):
        if self.recordingCameras:
            self.recordingCameras = []
        if self.alarmRecording:
            self.alarmRecording = []

    def _initFileMonitor(self):
        Log.info("_initFileMonitor==>>start")
        recordPath = ProfileFunc.getRecordPath()
        monitorPath = os.path.join(recordPath, SAVE_PATH)
        self.cameraFolderMonitor = CameraFolderMonitorThread(monitorPath,None)
        self.cameraFolderMonitor.start()
        Log.info("_initFileMonitor==>>end")
    
    def _getRecordTime(self, bt, et):
        bt, et = int(bt), int(et)
        if et < bt or et == bt:
            return [x for x in xrange(MINMINUTES,MAXMINUTES) if x >= bt or x < et]
        else:
            return [x for x in xrange(MINMINUTES,MAXMINUTES) if x >= bt and x < et] 
                 
    def _checkAutoRecording(self, min, camera, dayUpdate=False):
        if str(camera['record']) == '0':
            if camera["uid"] in self.recordingCameras:
                self._stopRecord(camera["uid"], camera['stream'])
            return
        if self._checkFullDiskSpace(camera["uid"], SPACE_TYPE.LOW_SPACE):
            Log.info("camera[%s] Low Space to Stop Recording at [%s]"%(camera["uid"], str(min)))
            self._stopRecord(camera["uid"], camera['stream'])
            return
        recording_times = []
        if camera['r1']:
            recording_times = self._getRecordTime(camera['r1'][0], camera['r1'][1])
            r1_end = int(camera['r1'][1])
        else:
            r1_end = -1
        if camera['r2']:
            recording_times += self._getRecordTime(camera['r2'][0], camera['r2'][1])
            r2_end = int(camera['r2'][1])
        else:
            r2_end = -1
        #Log.info("recording cameras[%s], alarm recording cameras [%s]"%(self.recordingCameras, self.alarmRecording))
        if min in recording_times and not camera["uid"] in self.recordingCameras and not camera["uid"] in self.alarmRecording:
            self._startRecord(uid=camera["uid"], stream=camera['stream'], first_time_end=r1_end, second_time_end=r2_end)
            Log.info("camera[%s] Start Recording at [%s]"%(camera["uid"], str(min)))
        elif not min in recording_times and camera["uid"] in self.recordingCameras and not camera["uid"] in self.alarmRecording:
            self._stopRecord(camera["uid"], camera['stream'])
            Log.info("camera[%s] Stop Recording at [%s]"%(camera["uid"], str(min)))
        elif dayUpdate and (camera["uid"] in self.recordingCameras or camera["uid"] in self.alarmRecording):
            self._stopRecord(camera["uid"], camera['stream'])
            Log.info("camera[%s] Stop Recording at [%s] update day..."%(camera["uid"], str(min)))
        elif camera["uid"] in self.alarmRecording and self.alarmRecordTime.has_key(camera["uid"]):
            hour, min = time.localtime().tm_hour, time.localtime().tm_min
            cur_mins = int(hour) * 60 + int(min)
            if cur_mins >= self.alarmRecordTime[camera["uid"]]:
                result = self._stopAlarmRecording(camera["uid"])
    
    def _checkAutoSnapshoot(self, min, camera):
        #Log.info("*****_checkAutoSnapshoot ")
        if self._checkFullDiskSpace(camera["uid"], SPACE_TYPE.LOW_SPACE):
            return
        monitoring_times = []
        if camera['r1']:
            monitoring_times = self._getRecordTime(camera['r1'][0], camera['r1'][1])

        if camera['r2']:
            monitoring_times += self._getRecordTime(camera['r2'][0], camera['r2'][1])

        interval = camera["interval"]
        if min in monitoring_times and interval and int(interval) != 0:
            if not self.intervals.has_key(camera["uid"]):
                self.intervals[camera["uid"]] = time.time()
            elif time.time() - self.intervals[camera["uid"]] >= int(interval) * 60:
                #self.Snapshot(camera["uid"])
                self.Snapshot(None,{"uid":camera["uid"]})
                self.intervals[camera["uid"]] = time.time()
        
    def _getAlarmRecordingTime(self):    
        hour, min = time.localtime().tm_hour, time.localtime().tm_min
        start_mins = int(hour) * 60 + int(min)
        end_mins = start_mins + 20
        if end_mins > MAXMINUTES-1:
            end_mins = end_mins - MAXMINUTES
        return start_mins, end_mins
    
    def _getReconnectCameraTime(self, reconn_mins = 0):
        hour, min = time.localtime().tm_hour, time.localtime().tm_min
        start_mins = int(hour) * 60 + int(min)
        end_mins = start_mins + int(reconn_mins)
        if end_mins > MAXMINUTES-1:
            end_mins = end_mins - MAXMINUTES
        return start_mins, end_mins
    
    def _startAlarmRecording(self, uid, end_mins):
        if not self.cameras:
            return False
        if not self.cameras.has_key(uid):
            return False
        filename = ".tmp_Warning_%Y-%m-%d_%H%M%S"
        result = self._startRecord(uid=uid, stream=self.cameras[uid]['stream'], filename=filename, \
                                   isAlarm = True, first_time_end=end_mins, second_time_end=-1)
        if result:
            return True
        else:
            return False
        
    def _stopAlarmRecording(self, uid):
        if not self.cameras:
            return False
        if not self.cameras.has_key(uid):
            return False
        result = self._stopRecord(uid, self.cameras[uid]['stream'])
        if result:
            if uid in self.alarmRecording:
                self.alarmRecording.remove(uid)
            if self.alarmRecordTime.has_key(camera["uid"]):
                del self.alarmRecordTime[camera["uid"]]
            return True
        else:
            return False
        
    def _alarmRecording(self, uid):
        if not self.cameras:
            return
        if not self.cameras.has_key(uid):
            return
        if uid in self.recordingCameras:
            self._stopRecord(uid, self.cameras[uid]['stream'])
        if not uid in self.alarmRecording:
            self.alarmRecording.append(uid)
        Log.info("[%s] start alarm Recording..."%uid)
        start_mins, end_mins = self._getAlarmRecordingTime()
        self.alarmRecordTime[uid] = end_mins        
        self._startAlarmRecording(uid, end_mins)
  
    def _checkFullDiskSpace(self, uid, lowspace=0):
        if not ProfileFunc.GetBoxDisks() or not uid or not self.cameras.has_key(uid):
            return True
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
        if UtilFunc.isLowDiskSpace(self.record_path, lowspace):
            diskpath = UtilFunc.getDiskPath(self.record_path)
            if not os.path.exists(diskpath):
                return True
            disk_space, used_space, max_space = UtilFunc.getLinuxDiskInfo(diskpath)
            if SPACE_TYPE.LOW_SPACE >= disk_space > SPACE_TYPE.FULL_SPACE:
                type = ALARM_TYPE.lOWSPACE_ALARM
                is_full = False
            elif SPACE_TYPE.FULL_SPACE >= disk_space:
                type = ALARM_TYPE.FULLSPACE_ALARM
                is_full = True
                if not ProfileFunc.GetBoxDisks() or not os.path.exists(diskpath):
                    return is_full
            else:
                is_full = False
                return is_full
            size = disk_space
            if self.diskALarmTime.has_key(uid) and (time.time() - self.diskALarmTime.get(uid, 0)) < DISK_ALARM_TIME:
                return is_full
            self.diskALarmTime[uid] = time.time()
            self._sendAlarmMsg(uid, type, None, size)
            return is_full
        else:
            return False
    
    def _sendAlarmMsg(self, uid, type, imagePath=None, size=0):
        Log.info("********** _sendAlarmMsg **********")
        if int(self.alarmStatus) == ALARM_STATUS.ALARM_OFF:
            Log.info("the alarm status is off !!!")
            return
        if not uid or not type or not self.cameras or not self.cameras.has_key(uid):
            return
        if self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return
        if not self.emails and not self.mobiles:
            return
        if type == ALARM_TYPE.CAMERA_ALARM:
            if not imagePath or not os.path.exists(imagePath):
                Log.info("imagePath not exists...[%s]"%imagePath)
                return
            if self.cameras[uid]['alias']:
                cameraName = self.cameras[uid]['alias']
            else:
                cameraName = self.cameras[uid]['uid']
            createShare = {}
            #createShare = json.loads(self.parent.fileservice.CreateShare(imagePath))
            createShare = _createShare(imagePath)
            if createShare and createShare.has_key('url'):
                shareLink = createShare['url']
                Log.info("on new alarm report sharelink = [%s]!!!"%shareLink)
            else:
                shareLink = ''
            args = "serialNo=" + ProfileFunc.getResource() + "&" + \
                    "type=" + str(type) + "&" + \
                    "cameraName=" + cameraName +"&" + \
                    "imagePath=" + imagePath +"&" + \
                    "shareLink=" + shareLink
        elif type == ALARM_TYPE.lOWSPACE_ALARM:
            args = "serialNo=" + ProfileFunc.getResource() + "&" + \
                    "type=" + str(type) + "&" + \
                    "size=" + str(size)
        elif type == ALARM_TYPE.FULLSPACE_ALARM:
            args = "serialNo=" + ProfileFunc.getResource() + "&" + \
                    "type=" + str(type)
        else:
            return
        alarminfos = []
        if self.emails:
            alarminfos.extend(self.emails)
        if self.mobiles:
            alarminfos.extend(self.mobiles)
        for alarminfo in alarminfos:
            args += ("&" + "clients=" + str(alarminfo))
        ret = UtilFunc.PostServerByStr("/accounts/sendSecurityAlarm", args)
        UtilFunc.getLogger().info("*** _sendAlarmMsg get hub ret: %s" % ret) 
        if ret['result'] != 0:
            Log.info("Send AlarmReport Failed! Reason[%s]" % ret['message']) 
        else:
            Log.info("Send AlarmReport SuccessFull!")
        
    def _syncCameraInfo(self, camera):
        item = {}
        if not camera:
            return item
        try:
            for i in xrange(len(CAMERA_INFO)):
                item.setdefault(CAMERA_INFO[i],camera[i])
            if self.cameras.has_key(item['uid']) and self.cameras[item['uid']]:
                self.cameras[item["uid"]]["islive"] = item['is_live']
                self.cameras[item["uid"]]["type"] = item['type']
                self.cameras[item["uid"]]["ip"] = item['ip']
                self._setConfig()
        except Exception, e:
            Log.exception("_sync camera info failed!!!!Reason[%s]"%e)
        return item
    
    def _addAllSignalReceiver(self):
        self.d_obj.connect_to_signal("on_new_cameras_list", self.onNewCameraList, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_camera_info", self.onNewCameraInfo, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_camera_network_info", self.onNewCameraNetworkInfo, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_camera_sensor_isp_info", self.onNewCameraSensorIspInfo, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_live_streaming_start", self.onHLSStart, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_live_streaming_stop", self.onHLSStop, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_recording_file", self.onNewRecordingFile, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_recording_stop", self.onRecordingStop, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_snapshot_file", self.onNewSnapshotFile, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_alarm_report", self.onNewAlarmReport, dbus_interface=BUS_INTERFACE)
        self.d_obj.connect_to_signal("on_new_async_call_response", self.onNewAsyncCallResponse, dbus_interface=BUS_INTERFACE) 
        self.d_obj.connect_to_signal("on_modify_password_response", self.onModifyPasswordResponse, dbus_interface=BUS_INTERFACE) 
    
    def _killCameraService(self):
        Log.info("*******_killCameraCtrlService********")
        curTime = time.time()
        if curTime - self.killCstime > KILL_CS_TIME:
            killCameraService()
            self.killCstime = time.time()
        else:
            return
    
    def start(self):
        self.stoped = False
    
    def stop(self):
        self.stoped = True
        time.sleep(2)
        os.system("killall -9 camera-ctrl-service")
        Log.info('Camera-Ctrl-Service Killed!')
        
    def onNewCameraList(self, cameras, **params):
        Log.info("Received New CameraList!")
        lock_serach.acquire()
        self.search_list = []
        self.recNewCamSuc = False
        values = self.cameras.values()
        for _camera in cameras:
            item = {}
            for i in xrange(len(CAMERA_INFO)):
                item.setdefault(CAMERA_INFO[i],_camera[i])
            if item['uid']:
                if self.cameras.has_key(item['uid']):
                    item['is_added'] = 1
                else:
                    item['is_added'] = 0
            else:
                for value in values:
                    if value['deviceId'] == item['deviceId']:
                        item['is_added'] = 1
                    else:
                        item['is_added'] = 0
            self.search_list.append(item)
        self.recNewCamSuc = True
        lock_serach.release()
        for camera in cameras:
            item = self._syncCameraInfo(camera)
        

    def onNewCameraInfo(self, camera, **params):
        Log.info("Received New CameraInfo")
        self._syncCameraInfo(camera)
    
    def onNewCameraNetworkInfo(self, netinfo, **params):
        Log.info("Received New NetWorkInfo")
        return
    
    def onNewCameraSensorIspInfo(self, ispinfo, **params):
        Log.info("Received New IspInfo")
        return
    
    def onHLSStart(self, uid, streamid, hlspath, **params):
        Log.info("Camera[%s] start Playing!"%uid)
        return
    
    def onHLSStop(self, uid, streamid, **params):
        Log.info("Camera[%s] Stop HLS Play!"%uid)
        return
    
    def onNewRecordingFile(self, uid, streamid, filename, **params):
        Log.info("*** onNewRecordingFile Camera[%s] Start New Recording[%s]!"%(uid, filename))
        #self._setScanFolder()
        self.createthumbnail(filename)
    
    def onRecordingStop(self, uid, streamid, **params):
        Log.info("Camera[%s] Stop Recording!"%uid)
        return

    def onNewSnapshotFile(self, uid, filename, **params):
        Log.info("Camera[%s] Take New Photo[%s]!"%(uid, filename))
        #self._setScanFolder()
        self.newSnapShortFile[uid] = True;
        self.createthumbnail(filename)
        return
    
    def onNewAlarmReport(self, uid, msg, arg, **params):
        uid = str(uid)
        Log.warning("Receive an AlarmReport By Camera[%s]!"%uid)
        if not self.cameras or not self.cameras.has_key(uid):
            Log.info("Camera is not bind !!!")
            return 
        if str(self.cameras[uid]["motiondetect"]) != "1":
            Log.info("Camera motiondetect is off !!!")
            return

        if self._checkFullDiskSpace(uid, SPACE_TYPE.LOW_SPACE):
            Log.info("Alarminfo has no disk space!!!")
            return
        if self.alarmtime.has_key(uid) and (time.time() - self.alarmtime.get(uid, 0)) < SEND_ALARM_TIME:
            return
        self.alarmtime[uid] = time.time() 
        
        name=time.strftime("Warning_%Y-%m-%d_%H%M%S", time.localtime()) + ".jpg"
        #self.Snapshot(uid, filename=name)
        self.Snapshot(None,{"uid":uid, "filename":name})
        save_path = self._getSavePath(uid)
        imagePath = save_path + "/" + name
        type = ALARM_TYPE.CAMERA_ALARM 
        self.WaitRecNewSnapShortFile(uid)
        self._sendAlarmMsg(uid, type, imagePath)
        self._alarmRecording(uid)

    
    def onNewAsyncCallResponse(self, token, uid, stream_id, method_name, error_code, text_info):
        Log.info("receive one async respose with Token[%s], text_info[%s]" % (token, text_info))
        self.msgs[token] = text_info
        if("camera disconnect" == text_info):
            #Log.info("receive camera[%s] disconnect ..." % uid)    
            #self._reConnectCamera(uid)
            if not self.login.has_key(uid):
                self.login[uid] = {}
            if (self.login[uid].has_key("login") and self.login[uid]["login"]) or not self.login[uid].has_key("login"):
                Log.info("receive camera[%s] disconnect ..." % uid)
                start_times, reconntimes = self._getReconnectCameraTime(2)
                self.login[uid]["login"] = False
                self.login[uid]["reconntime"] = reconntimes
#                Log.info("receive camera[%s] disconnect reconntimes = %d ..." % (uid, reconntimes))
        elif "camera relay mode" == text_info:
            if not self.cameras.has_key(uid):
                return
            if not self.login.has_key(uid):
                self.login[uid] = {}
            if self.login[uid].has_key("login") and self.login[uid]["login"] and (not self.login[uid].has_key('relaymode') or (self.login[uid].has_key('relaymode') and not self.login[uid]['relaymode'])):
                Log.info("receive camera[%s] relay mode ..." % uid)
                start_times, reconntimes = self._getReconnectCameraTime(2)
                self.login[uid]['relaymode'] = True
                self.login[uid]['relayreconntime'] = reconntimes
                
    def onModifyPasswordResponse(self, uid, result):
        Log.info("receive modify password responce[%s]" % uid)
        self.recModifyPwdResp[uid] = True
        self.modifyPwdResult[uid] = int(result)
        if(self.modifyPwd.has_key(uid) and self.modifyPwd[uid].has_key("newpwd")):
            self.SetCameraPwd(uid, self.modifyPwd[uid]["newpwd"])
    
    def syncCameras(self, uid, camera):
        self._initCameraInfo(uid, camera = camera)
        self._initBindedCamera(uid)
        self._setConfig()
    
    def _initBindedCamera(self, uid):
        if not uid or not self.cameras.has_key(uid):
            return False
        camera = {}
        cameras = {}
        camera = self.cameras[uid]
        #cameras["cameras"] = [camera]
        self.login[uid] = {}
        
        if camera.has_key("password"):
            camera["password"] = str(camera["password"])
                    
        try:
            result = self.d_obj.add_camera_ex(json.dumps(camera), dbus_interface=BUS_INTERFACE)
            #print "**** _initBindedCamera result = %d"%result
            if result == 0:
                self.login[uid]["login"] = True;
                return True
            elif result == -2:
                start_times, reconntimes = self._getReconnectCameraTime(2)
                self.login[uid]["login"] = False;
                self.login[uid]["reconntime"] = reconntimes
                return True
            else:
                start_times, reconntimes = self._getReconnectCameraTime(2)
                self.login[uid]["login"] = False;
                self.login[uid]["reconntime"] = reconntimes
                return False
        except Exception, e:
            Log.exception("_initBindedCamera Failed! Reason[%s]"%e)
            if DBUS_NORLY in str(e):
                Log.exception("_initBindedCamera kill camera service")
                self._killCameraService()
            return False

    def _reConnectCamera(self, uid):
        if not uid:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        #Log.info("*** _reConnectCamera uid: %s!!!"%uid)        
        info = {}
        try:
            info["uid"] = uid
            info["password"] = str(self.cameras[uid]["password"])
            self.d_obj.stop_camera_recording(self._gettoken(), uid, int(self.cameras[uid]['stream']), \
                                                      dbus_interface=BUS_INTERFACE)
            #result = self.d_obj.set_camera_password(json.dumps(info), dbus_interface=BUS_INTERFACE)
            result = self.d_obj.camera_relogin(json.dumps(info), dbus_interface=BUS_INTERFACE);
            Log.info("*** _reConnectCamera uid result: %d!!!"%result) 
            if uid in self.recordingCameras:
                self.recordingCameras.remove(uid)
            if uid in self.alarmRecording:
                self.alarmRecording.remove(uid)
            
            if not self.login.has_key(uid):
                    self.login[uid] = {}        
            
            self.login[uid]["relaymode"] = False;
            
            if 0 ==  result:       
                self.login[uid]["login"] = True;
                return self._jsonResult()
            else:
                start_times, reconntimes = self._getReconnectCameraTime()
                self.login[uid]["login"] = False;
                self.login[uid]["reconntime"] = reconntimes
                return self._jsonError(530)
        except Exception,e:
            Log.exception("Camera[%s] _reConnectCamera Failed! Reason[%s]"%(uid,e))
            if DBUS_NORLY in str(e):
                Log.exception("Set Camera password kill camera service")
                self._killCameraService()
            return self._jsonError(528)


    def _setConfig(self):
        cf = ConfigParser.ConfigParser()
        cf.add_section('profile')
        cf.set("profile", "daystime",   self.daystime)
        cf.set("profile", "recordpath", self.record_path)
        cf.set("profile", "mobiles",    json.dumps(self.mobiles))
        cf.set("profile", "emails",     json.dumps(self.emails))
        cf.set("profile", "alarmStatus",self.alarmStatus)
        for (camera, info) in self.cameras.items():
            if not cf.has_section(camera):
                cf.add_section(camera)
                for (key, value) in info.items():
                    if isinstance(value, types.ListType):
                        value = json.dumps(value)
                    cf.set(camera, key, value)
        cf.write(open(CONFIG_PATH, "w+"))
    
    def _getConfigOption(self, obj, section, option):
        if not obj or not section or not option:
            return ''
        try:
            if obj.has_option(section, option):
                opt = obj.get(section, option)
                try:
                    return json.loads(opt)
                except:
                    return opt
            else:
                return ''
        except Exception, e:
            Log.exception("_getConfigOption Failed! Reason[%s]"%e)
            return ''

    def _parseConfig(self):
        if not os.path.exists(CONFIG_PATH):
            self._setConfig()
        else:
            try:
                cf = ConfigParser.ConfigParser()
                cf.read(CONFIG_PATH)
                self.daystime       = int(self._getConfigOption(cf, "profile", "daystime"))
#                self.record_path    = self._getConfigOption(cf, "profile", "recordpath") 
                self.record_path    = ProfileFunc.getRecordPath()
                self.mobiles        = self._getConfigOption(cf, "profile", "mobiles")
                self.emails         = self._getConfigOption(cf, "profile", "emails")
                self.alarmStatus    = self._getConfigOption(cf, "profile", "alarmStatus")
                for section in cf.sections():
                    if section == 'profile':
                        continue
                    camera = {}
                    for key in BIND_INFO:
                        camera[key] = self._getConfigOption(cf, section, key)
                    self.syncCameras(camera['uid'], camera)
            except Exception,e:
                Log.exception("parseConfig Failed! Reason[%s]"%e)
                self._setConfig()

    
    def _getRmoteObject(self):
        return self.dbus.get_object(BUS_NAME, BUS_PATH)
        
    def _getInterFace(self):
        return dbus.Interface(self.d_obj, BUS_INTERFACE)     

    def _gettoken(self):
        current_token = self.token
        self.token += 1
        return current_token
        
    def _getSavePath(self, uid, alias=None):
        folder = time.strftime("%Y-%m-%d", time.localtime())
        if not uid:
            return None
        if not ProfileFunc.GetBoxDisks():
            return None
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
            Log.info("*** _getSavePath self.record_path : %s!!!"%self.record_path)
        name = uid
        record_path = os.path.join(self.record_path, SAVE_PATH)
        save_path = os.path.join(record_path, name, folder).replace("\\", "/")
        return save_path

    def _setScanFolder(self):
        if not ProfileFunc.GetBoxDisks():
            return
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
        scan_path = os.path.join(self.record_path, SAVE_PATH)
        if not os.path.exists(scan_path) and ProfileFunc.GetBoxDisks():
            os.makedirs(scan_path)
        disk = UtilFunc.getDiskPath(scan_path)
        needscanfolders = ProfileFunc.getMediaFolder(disk)
        
        if not scan_path in self.scanFolder:
            self._addScanFolder(scan_path)
        else:
            return
        
#        if needscanfolders and not scan_path in needscanfolders:
##             ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder([scan_path],[])
#             self._addScanFolderSubLibrary(scan_path, needscanfolders)       
#        else:
#            return

    
    def _addScanFolderSubLibrary(self, folder_path, need_scan_folders=[]):
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return

        ProfileFunc._execSql(ProfileFunc.getneedscanfolderDB(UtilFunc.getDiskPath(folder_path)),\
                                "replace into mediafolder(url, type) values(?,?)", (folder_path, 'all',)) 
#        print "######### _addScanFolder2 folder_path = %s"%folder_path
        for scan_path in os.listdir(folder_path):
            scan_path = os.path.join(folder_path, scan_path)

            if os.path.isdir(scan_path):
                if not scan_path in need_scan_folders: 
                    self._addScanFolderSubLibrary(scan_path) 
            else:
                continue
            
    def _addScanFolder(self, folder_path):
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return
        self.scanFolder.append(folder_path)
        for scan_path in os.listdir(folder_path):
            scan_path = os.path.join(folder_path, scan_path)
            if os.path.isdir(scan_path):
                if not scan_path in self.scanFolder:
                    print scan_path 
                    self._addScanFolder(scan_path) 
            else:
                continue

    def _initCameraDB(self):
        if not ProfileFunc.GetBoxDisks():
            return
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
        scan_path = os.path.join(self.record_path, SAVE_PATH)
        if not os.path.exists(scan_path) and ProfileFunc.GetBoxDisks():
            os.makedirs(scan_path)
        
        CameraUtils.setCameraPath(scan_path)
        CameraUtils.initCameraDB()
        CameraUtils.updateCameraDB(0, None, True)
    
#    def _scanCameraFolder(self):
#        if not ProfileFunc.GetBoxDisks():
#            return
#        
#        if not self.record_path:
#            self.record_path = ProfileFunc.getRecordPath()
#        folder_path = os.path.join(self.record_path, SAVE_PATH)
#        
#        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
#            return
#                
#        for sub_path in os.listdir(folder_path):
#            scan_path = os.path.join(folder_path, sub_path)
#            
#            if UtilFunc.isHiddenFile(scan_path) or sub_path[:5] == ".popo" or sub_path[:4] == ".tmp":
#                continue
#            
#            if os.path.isdir(scan_path):
#                print scan_path
#                self._scanCameraFolder(scan_path)
#                continue
#            
#            CameraProfileFunc.addCameraFileCache(scan_path)
                
    def _scanCameraFolder(self):
        if not self.scanFolder:
            return
        
        for scan_folder in self.scanFolder:
            if os.path.isdir(scan_folder):
                for sub_path in os.listdir(scan_folder):
                    scan_path = os.path.join(scan_folder, sub_path)
                    if os.path.isdir(scan_path):
                        continue
                    if UtilFunc.isHiddenFile(scan_path) or sub_path[:5] == ".popo" or sub_path[:4] == ".tmp":
                        continue
                    CameraUtils.addCameraFileCache(scan_path)
        CameraUtils.delCameraDBWithIsExist()
     
    def _initCameraInfo(self, uid, devId='', mft='', hw='', ver='', id=0, type='', ip='', alias='', password='admin', camera={}):
        Log.info("****_initCamera **** self.cameras = [%s]!"%self.cameras)
        if not uid:
            return
        if not camera:
            self.cameras[uid] = {
                    "type"         :type,
                    "uid"          :uid,
                    "deviceId"     :devId,
                    "ip"           :ip,
                    "mft"          :mft,
                    "ver"          :ver,
                    "hw"           :hw,
                    "alias"        :alias,
                    "record"       :'1', 
                    "records"      :"/sdcard", 
                    "daystime"     :self.daystime, 
                    "motiondetect" :'1',
                    "sensitive"    :'1',
                    "interval"     :'30', 
                    "r1"           :[540,1080], 
                    "r2"           :[],
                    "week"         :[0, 1, 2, 3, 4],
                    "stream"       :'1', 
                    "islive"       :'1',
                    "password"     :password}
        else:
            if not self.cameras or not self.cameras.has_key(uid):
                self.cameras[uid] = camera
            else:
                for key in self.cameras[uid].keys():
                    if camera.has_key(key):
                        self.cameras[uid][key] = camera[key]
    
    def _startRecord(self, uid, stream=1, path="", isAlarm = False, filename=".tmp_Record_%Y-%m-%d_%H%M%S", duration=1200, first_time_end=-1, second_time_end=-1):
        if not ProfileFunc.GetBoxDisks():
            return False
        elif self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return False
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
            Log.info("_startRecord self.record_path : %s!!!"%self.record_path)
        if UtilFunc.isLowDiskSpace(self.record_path, 120 * len(self.cameras.keys()) * 1024):
            Log.info("Disk Haven't Enough Space For Recording! Please Clean it!")
            return False
        if not path:
            path = self._getSavePath(uid)
        save_path = path
        Log.info("_startRecord Message: uid[%s] stream[%s] save_path[%s] records[%s]"%(uid,stream,save_path,self.cameras[uid]['records']))
        if not os.path.exists(save_path): os.makedirs(save_path)
        if self.cameras[uid]['records'] != save_path:
#            self.SetRecordConfig(uid, int(stream), save_path)
            self.cameras[uid]['records'] = save_path
            self._setConfig()
        info = {}
        info["uid"] = uid
        info["deviceId"] = str(self.cameras[uid]["deviceId"])
        info["token"] = self._gettoken()
        info["stream_id"] = int(stream)
        info["recording_path"] = save_path
        info["recording_filename_pattern"] = filename
        info["mft"] = str(self.cameras[uid]["mft"])
        info["hw"] = str(self.cameras[uid]["hw"])
        info["ver"] = str(self.cameras[uid]["ver"])
        info["max_record_duration"] = int(duration)
        info["first_time_end"] = int(first_time_end)
        info["second_time_end"] = int(second_time_end)
        info["password"] = str(self.cameras[uid]["password"])
        
        try:
            result = self.d_obj.start_camera_recording_ex(json.dumps(info), dbus_interface=BUS_INTERFACE)
            Log.info("_startRecord result = %s"%result)
            if result == 0:
                if isAlarm:
                    if not uid in self.alarmRecording:
                        self.alarmRecording.append(uid)
                else:
                    if not uid in self.recordingCameras: 
                        self.recordingCameras.append(uid)
                return True
            else:
                return False
        except Exception,e:
            if isAlarm:
                if uid in self.alarmRecording:
                    self.alarmRecording.remove(uid)
            Log.error("_startRecord Failed! Reason[%s]"%e)
            if DBUS_NORLY in str(e):
                Log.exception("start record Ex kill camera service")
                self._killCameraService()
            return False

    def _stopRecord(self, uid, stream=1):
        Log.info("_stopRecord Message: uid[%s] stream[%s]"%(uid,stream))
        try:
            result = self.d_obj.stop_camera_recording(self._gettoken(), uid, int(stream), \
                                                      dbus_interface=BUS_INTERFACE)
            Log.info("**** _stopRecord result = %s"%result)
            if 0 == result:                    
                if uid in self.recordingCameras:
                    self.recordingCameras.remove(uid)
                if uid in self.alarmRecording:
                    self.alarmRecording.remove(uid)
                return True
            else:
                return False
        except Exception,e:
            Log.error("_stopRecord Failed! Reason[%s]"%e)
            if DBUS_NORLY in str(e):
                Log.exception("stop record kill camera service")
                self._killCameraService()
            return False
    
    def _createShare(self, path, isPrivate=True, validity=-1):
        if not path:
            return None

        if not os.path.exists(path):
            return None

        isdir = int(os.path.isdir(path))
        if not isdir:
            ext = UtilFunc.getFileExt(path)
            size = os.path.getsize(path)
        else:
            ext = ""
            size = 0
        location = path.replace('\\', '/')
        name = os.path.basename(path)
        access = ''
        if isPrivate:
            access = ''.join([str(random.randint(0,9)) for x in xrange(4)])
        shareId = uuid.uuid4().hex
        url = WebFunc.getShareUrl(shareId, isPrivate, validity)
        if not url:
            return None
        lastModify = os.stat(location).st_mtime
        ret = ProfileFunc.addShare(shareId, location, url, name, ext, isdir, access, validity, size)
        if not ret:
            return None
        ret= {
            'id': url,
            'location': location,
            'name': name,
            'contentType':ext,
            'isFolder': isdir,
            'extractionCode':access,
            'validity': validity,
            'lastModify': os.path.getmtime(location),
            'contentLength':size
            }
        
        return ret
    
    def _getThumbHash(self, filePath, size=170):
        filePath = filePath.replace('\\', '/')
        if not os.path.exists(filePath):
            return (None, None)
        
#        savePath = os.path.join(UtilFunc.getDiskPath(filePath),'.popoCloud')
#        if UtilFunc.matchFilter(os.path.basename(filePath), filters['picture']):
#            fileType = 'picture'
#            minhash = UtilFunc.getMd5Name(filePath, MinWidth, MinHeight)
#            maxhash = UtilFunc.getMd5Name(filePath, MaxWidth, MaxHeight)
#        elif UtilFunc.matchFilter(os.path.basename(filePath), filters['video']):
#            Log.info("********* _getThumbHash video filePath = %s"%filePath)
#            fileType = 'video'
#            (folder, filename) = os.path.split(filePath)
#            image_path = os.path.join(folder, '.tmp_' + md5.md5(repr(filename)).hexdigest() + '.bmp')
#            minhash = UtilFunc.getMd5Name(image_path, MinWidth, MinHeight)
#            maxhash = UtilFunc.getMd5Name(image_path, MaxWidth, MaxHeight)
#        else:
#            return (None, None)
        if UtilFunc.matchFilter(os.path.basename(filePath), filters['picture']) or UtilFunc.matchFilter(os.path.basename(filePath), filters['video']):
            minhash = UtilFunc.getMd5Name(filePath, MinWidth, MinHeight)
            maxhash = UtilFunc.getMd5Name(filePath, MaxWidth, MaxHeight)
        else:
            return (None, None)
        
        return (minhash, maxhash)
        
    def _getFileList(self, parentFolder, extInfo):
        files = []
        for filename in os.listdir(parentFolder):
            fileFullPath = os.path.join(parentFolder, filename)
            if UtilFunc.isHiddenFile(fileFullPath) or filename[:5] == ".popo" or filename[:4] == ".tmp":
                continue
            parentFolder = UtilFunc.getParentPath(fileFullPath)
            fileInfo = self._getFileInfo(fileFullPath, extInfo)
            if not fileInfo :
                Log.debug("get %s file info failed"%repr(fileFullPath))
                continue
            print "_getFileList fileInfo = %s"%fileInfo
            fileInfo['minHash'], fileInfo['maxHash'] = self._getThumbHash(fileFullPath)
            
            files.append(fileInfo)   
        
        if extInfo:
            if len(extInfo['orderBy']) > 0:
                files.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, extInfo['orderBy'])) 
            if extInfo.has_key('limit') and extInfo.has_key('offset'):
                if extInfo['limit'] >= 0:
                    files = files[extInfo['offset']:(extInfo['limit'] + extInfo['offset'])]
                else:
                    files = files[extInfo['offset']:]
    
        return files
        
    def _getFileInfo(self, fileFullPath, extInfo):
        fileShortPath = UtilFunc.getShortPath(fileFullPath)
        if not UtilFunc.IsMediaInserted(fileShortPath):
            return None
    
        if UtilFunc.isShorcut(fileShortPath):
            fileFullPath = UtilFunc.getShortcutRealPath(fileShortPath)
            fileShortPath = UtilFunc.getShortPath(fileFullPath)
        
        if extInfo and UtilFunc.isWindowsSystem() and len(fileShortPath) > 3:
            import win32file, win32con
            try:
                fileAttr = win32file.GetFileAttributes(fileShortPath)
            except:
                Log.error(traceback.format_exc())
                fileAttr = -1
    
            if fileAttr == -1:
                import win32api
                err = win32api.GetLastError()
                Log.debug("Invaild Attribute,File:%s,error=%d", repr(fileShortPath), err)
                return None
            else:
                if not extInfo['showHideFile'] and (fileAttr & win32con.FILE_ATTRIBUTE_HIDDEN) :
                    Log.debug("Hidden File:%s", repr(fileShortPath))
                    return None
                if not extInfo['showSystemFile'] and (fileAttr & win32con.FILE_ATTRIBUTE_SYSTEM):
                    Log.debug("System File:%s", repr(fileShortPath))
                    return None
        
        fileInfo = UtilFunc.formatFileInfo(fileFullPath)
        if extInfo and extInfo.has_key('filter') and extInfo['filter'] == 'image':
            if not os.path.isfile(fileShortPath): 
                fileInfo['isadd'] = ProfileFunc.isMediaFolder(fileShortPath)
            elif not UtilFunc.isPicturePath(fileShortPath):
                return None
        return fileInfo
    

    def _jsonResult(self, ret=None):
        if not ret:
            return {"result":0}
        
        if isinstance(ret, types.DictType):
            if 'result' not in ret:
                ret['result'] = 0
            return ret
    
        if isinstance(ret, types.ListType):
            return {'result':0, "data":ret}
        
    def _jsonError(self, error_code):
        return {'error_code':error_code}

    def GetInfo(self, args, params):
        uid = params.get('uid', None)
        if not uid:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        if self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)

        return self._jsonResult(self.cameras[uid])


    def Add(self, args, params):
        camera = params.get('camera', None)
        if not camera:
            return self._jsonError(460)
        
        try:
            camera = json.loads(camera)
        except Exception, e:
            Log.exception("Add Cameras json parse failed! Reason[%s]"%e)
            return self._jsonError(460)
        
        uid = camera["uid"]
        
        if not camera.has_key("password") or not camera["password"]:
            camera["password"] = "admin"
        
        if self.cameras.has_key(uid):
            return self._jsonError(523)
        
        if self.addingcameras and uid in self.addingcameras:
            Log.info("Add_Ex Camera [%s] is adding!!!!!"%uid)
            return self._jsonError(524)
        
        self.login[uid] = {}
        try:
            self.addingcameras.append(uid)
            Log.info("Camera is adding...")
            result = self.d_obj.add_camera_ex(json.dumps(camera), dbus_interface=BUS_INTERFACE)
            if 0 == result:
                self._initCameraInfo(camera["uid"], camera["deviceId"], camera["mft"], camera["hw"], \
                                     camera["ver"], 0, int(camera["type"]), camera["ip"], camera["alias"], camera["password"])
                self._setConfig()
                if self.addingcameras and uid in self.addingcameras:
                    self.addingcameras.remove(uid)
                if result == 0:
                    self.login[uid]["login"] = True;
                else:
                    self.login[uid]["login"] = False;
                return self._jsonResult({"result":0, "info":self.cameras[uid]})
            elif -2 == result:
                self._initCameraInfo(camera["uid"], camera["deviceId"], camera["mft"], camera["hw"], \
                                     camera["ver"], 0, int(camera["type"]), camera["ip"], camera["alias"], camera["password"])
                self.login[uid]["login"] = False;
                if self.addingcameras and uid in self.addingcameras:
                    self.addingcameras.remove(uid)
                #return self._jsonError(521)
                return self._jsonResult({"result":0, "info":self.cameras[uid]})
            elif -20009 == result:
                if self.addingcameras and uid in self.addingcameras:
                    self.addingcameras.remove(uid)
                return self._jsonError(521)
            else:
                if self.addingcameras and uid in self.addingcameras:
                    self.addingcameras.remove(uid)
                return self._jsonError(525)
        except Exception,e:
            Log.exception("Add_Ex Failed! Reason[%s]"%e)
            if self.addingcameras and uid in self.addingcameras:
                self.addingcameras.remove(uid)
            if DBUS_NORLY in str(e):
                UtilFunc.getLogger().exception("Add_Ex kill camera service")
                self._killCameraService()
            return self._jsonError(525)

    def Rename(self,args, params):
        uid = params.get("uid", None)
        alias = params.get('alias', "")
        
        if not uid:
            return self._jsonError(460)
        elif not self.cameras.has_key(uid):
            return self._jsonError(520)
        elif self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)
        old_name = self.cameras[uid]["alias"]
        if old_name == alias:
            return self._jsonResult()
        self.cameras[uid]["alias"] = alias
        return self._jsonResult()
    
    
    def Remove(self, args, params):
        uid = params.get('uid', None)
        if not uid:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        if self.removeingcameras and uid in self.removeingcameras:
            return self._jsonError(526)
        try:
            self.removeingcameras.append(uid)
            if uid in self.recordingCameras or uid in self.alarmRecording: 
                #self._stopRecord(uid, self.cameras[uid]['stream'])
                self.d_obj.stop_camera_recording(self._gettoken(), uid, int(self.cameras[uid]['stream']), \
                                                      dbus_interface=BUS_INTERFACE)
            self.d_obj.del_camera(self._gettoken(), uid, dbus_interface=BUS_INTERFACE)
            
            del self.cameras[uid]
            if uid in self.recordingCameras:
                self.recordingCameras.remove(uid)
            if uid in self.alarmRecording:
                self.alarmRecording.remove(uid)
            if self.login.has_key(uid): del self.login[uid]
            if self.alarmtime.has_key(uid): del self.alarmtime[uid]
            if self.diskALarmTime.has_key(uid): del self.diskALarmTime[uid]
            if self.intervals.has_key(uid): del self.intervals[uid]
            if self.alarmRecordTime.has_key(uid): del self.alarmRecordTime[uid]

            self._setConfig()
            
            if self.removeingcameras and uid in self.removeingcameras:
                self.removeingcameras.remove(uid)
                
            return self._jsonResult()
        except Exception,e:
            if self.removeingcameras and uid in self.removeingcameras:
                self.removeingcameras.remove(uid)
            Log.exception('Remove Failed! Reason[%s]'%e)
            if DBUS_NORLY in str(e):
                Log.exception("Remove kill camera service")
                self._killCameraService()
            return self._jsonError(528)
    
    
    def List(self, args, params):
        tmp_list = []
        for uid in self.cameras.keys():
            if self.cameras[uid]:
                tmp_list.append(self.cameras[uid])
        return self._jsonResult({"result":0, "data":tmp_list})


    '''
    @param uid: camera uid.
    @param streamid: record quality. useless for the moment. 
    @param path: The path of video files. 
    @param filename: The record file name rules.
    @param duration: The video time.
    '''
    def SetRecordConfig(self, args, params):
        uid = params.get('uid', None)
        streamid = int(params.get('streamid', 1))
        path = params.get('path', "")
        filename = params.get('filename', ".tmp_Record_%Y-%m-%d_%H%M%S")
        duration = int(params.get('duration', 1200))
        
        if not uid:
            return self._jsonError(460)
        
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
    
        if self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)
        
        if not path:
            path = self._getSavePath(uid)
        try:
            token = self._gettoken()
            self.d_obj.set_camera_recording_config(token, uid, int(streamid), path, filename, \
                                                   int(duration), dbus_interface=BUS_INTERFACE)
            if self.cameras[uid]:
                self.cameras[uid]["records"] = path
                if int(self.cameras[uid]["stream"]) != int(streamid):
                    self._stopRecord(uid, self.cameras[uid]["stream"])
                self.cameras[uid]["stream"] = streamid
            self._setConfig()
            return self._jsonResult()
        except Exception, e:
            Log.exception('Set Record Config Failed! Reason[%s]'%e)
            if DBUS_NORLY in str(e):
                Log.exception("Set Record Config kill camera service")
                self._killCameraService()
            return self._jsonError(528)    


    def SetInterval(self, args, params):
        uid = params.get('uid', None)
        interval = params.get('interval', 30)
        
        ret = self.Verify(uid)
        if ret: return ret
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
        if UtilFunc.isLowDiskSpace(self.record_path, 100 * 1024):
            return self._jsonError(467)
        if int(interval) < 0:
            return self._jsonError(460)
        self.cameras[uid]["interval"] = str(interval)
        self.intervals[uid] = time.time()
        self._setConfig()
        self.Snapshot(args,params)
        return self._jsonResult()
    
    def SetMobile(self, args, params):
        mobiles = params.get('mobiles', None)
        try:
            self.mobiles = json.loads(mobiles)
        except Exception,e:
            Log.exception('SetMobile Failed! Reason[%s]'%e)
            return self._jsonError(460)
        self._setConfig()
        return self._jsonResult()

    def GetMobiles(self, args, params):
        return self._jsonResult({'result':0,'mobiles':self.mobiles})

    def SetEmail(self, args, params):
        emails = params.get('emails', None)
        try:
            self.emails = json.loads(emails)
        except Exception,e:
            Log.exception('SetEmail Failed! Reason[%s]'%e)
            return self._jsonError(460)
        self._setConfig()
        return self._jsonResult()

    def GetEmails(self, args, params):
        return self._jsonResult({'result':0,'emails':self.emails})

    def SetAlarmInfo(self, args, params):
        alarmInfo = params.get('alarmInfo', None)
        if not alarmInfo:
            return self._jsonError(460)
        try:
            self.alarminfo = json.loads(alarmInfo)
        except Exception,e:
            Log.exception('SetAlarmInfo Failed! Reason[%s]'%e)
            return self._jsonError(460)
        self._setConfig()
        return self._jsonResult()

    def GetAlarmInfo(self, args, params):
        return self._jsonResult({'result':0, 'alarminfo':self.alarminfo})

    def SetRegular(self, args, params):
        #set Recording regular
        uid = params.get('uid', None)
        fi = params.get('fi', '[540, 1080]')
        se = params.get('se', '[]')
        week = params.get('week', '[0,1,2,3,4]')
        
        ret = self.Verify(uid)
        if ret: return ret
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
            
        if UtilFunc.isLowDiskSpace(self.record_path, 120 * len(self.cameras.keys()) * 1024):
            return self._jsonError(467)
        
        camera = self.cameras[uid]
        try:
            camera["r1"]    = json.loads(fi)
            camera["r2"]    = json.loads(se)
            camera['week']  = json.loads(week)
        except Exception,e:
            Log.exception('Json Loads Failed! Reason[%s]'%e)
            return self._jsonError(460)
        if uid in self.recordingCameras or uid in self.alarmRecording:
            self._stopRecord(uid, self.cameras[uid]['stream'])
        self._setConfig()
        return self._jsonResult()

    def RecordsList(self, args, params):
        name = params.get('name', None)
        extInfo = params.get('extInfo', None)
        
        if not ProfileFunc.GetBoxDisks():
            return self._jsonError(465)
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
        if not name:
            parent_path = os.path.join(self.record_path, SAVE_PATH)
            #return self.parent.fileservice._getFileList(parent_path)
            #return self._getFileList(parent_path, extInfo)
            files = self._getFileList(parent_path, extInfo)
            return self._jsonResult({"result":0, "files":files})
        else:
            path = os.path.join(self.record_path, SAVE_PATH, name)
        if not os.path.exists(path):
            return self._jsonError(464)
        tmp_list = []
        for folder in os.listdir(path):
            folder_info = {}
            folder_path = os.path.join(path, folder)
            if not os.path.isdir(folder_path):
                continue
            p_count, v_count = 0,0
            for file in os.listdir(folder_path):
                if file.startswith("."):
                    continue
                ext = UtilFunc.getFileExt(os.path.join(folder_path,file))
                if ext == "jpg":
                    p_count += 1
                elif ext == "mp4":
                    v_count += 1
            folder_info.setdefault("path", folder_path)
            folder_info.setdefault("photos", p_count)
            folder_info.setdefault("videos", v_count)
            tmp_list.append(folder_info)
            
        tmp_list.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, [['path', -1]]))
        return self._jsonResult({"result":0, "folders":tmp_list})
    
    def FileList(self, params):
        path = params.get('path', None)
        extInfo = params.get('extInfo', None)
        Log.info("**** FileList extInfo = %s"%extInfo)
        
        if extInfo:
            try:
                extInfo = json.loads(extInfo)
            except:
                extInfo = extInfo
            
        if not path:
            return self._jsonError(460)
        if not os.path.exists(path):
            return self._jsonError(464)
        
        files = []
        files = self._getFileList(path, extInfo)
        return self._jsonResult({"result":0, "files":files})
    
    def formatPhotoRet(self, orderBy, datas):
        ret = []
        for fileInfo in datas:
            path = UtilFunc.toLinuxSlash(fileInfo['url'])
            if not os.path.exists(path):
                continue
            ret.append({'url'           :path,
                        'minHash'       :fileInfo['minHash'],
                        'maxHash'       :fileInfo['maxHash'],
                        'name'          :fileInfo['name'],
                        'lastModify'    :fileInfo['lastModify'],
                        'contentLength' :fileInfo['contentLength'],
                        'idCode'        :fileInfo['idCode'],
                        'contentType'   :UtilFunc.getFileExt(path)
                        })
        if orderBy:
            cmpInfo = UtilFunc.httpArgToCmpInfo(orderBy)
            if len(cmpInfo) > 0 :
                ret.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, cmpInfo))
        
        return ret
    
    def FileListfromDB(self, args, params):
        path = params.get('path', None)
            
        if not path:
            return self._jsonError(460)
        if not os.path.exists(path):
            return self._jsonError(464)
        
        ret = CameraUtils.getDBDataByFolder(path)
        files = self.formatPhotoRet(params.get('order',None),ret)
        
        return self._jsonResult({"result":0, "files":files})
        
    def DownloadThumb(self, args, params):
#        hash = params.get('hash', None)
#        if not hash:
#            return self._jsonError(460)
#        
#        tempThumbImage = UtilFunc.getPictureHashPath(hash)
#        if not tempThumbImage or not os.path.exists(tempThumbImage):
#            raise cherrypy.HTTPError(464, 'Not Exist')
#
#        return static.serve_file(tempThumbImage,thumbnail.getImageTypes()['.jpg'])
        pass
        
    def GetAlbum(self, args, params):
        if not args :
            return self._jsonError(460)
        groupType = args[0]
        time = None
        if len(args) ==2:
            time = args[1]
        if groupType in ['month','week']:
            if not time:
                return self._getAlbumGroup( groupType, params)
            else:
                return self._getAlbumGroupDetail( groupType, time, params)
        else:
            return self._jsonError(460)

    def _getAlbumGroup(self, groupType, params):
        groups =[]
        uid = params.get('uid',None)
        orderBy = params.get('order','desc')
        start = params.get('start',0)
        limit = params.get('limit',-1)
        if uid != None:
            sqlStr = 'select %s, count(*) from (select * from fileCache where fileType="picture" and uid = "%s") group by %s order by %s %s'%(groupType,uid,groupType,groupType,orderBy)+' limit %s,%s'%(start,limit)
        else:
            sqlStr = 'select %s, count(*) from (select * from fileCache where fileType="picture") group by %s order by %s %s'%(groupType,groupType,groupType,orderBy)+' limit %s,%s'%(start,limit)
        groups = CameraUtils.execCameraSql(sqlStr,None)
        ret, ret_count, tmp_ret_dict = [], 0, {}
        for fileInfo in groups:
            ret.append({
                        'name'  : fileInfo[groupType],
                        'total' : fileInfo['count(*)']})
        if orderBy:
            cmpInfo = UtilFunc.httpArgToCmpInfo(orderBy)
            if len(cmpInfo) > 0 :
                ret.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, cmpInfo))        
        return  self._jsonResult({"result":0,'album':ret})
        
        
            
    def _getAlbumGroupDetail(self, groupType, date, params):
        uid = params.get('uid',None) 
        order = params.get('order','desc')
        start = params.get('start',0)
        limit = params.get('limit',-1)
        sqlStr = 'select * from fileCache where fileType= "picture"'
        if uid != None:
            sqlStr = sqlStr+' and uid = "%s"'%uid
        if groupType == "week":
            if date == '0' or date.startswith('-'):
                argTime = int(date)
                yearWeek = time.strftime("%Y-%W",time.localtime(time.time()+3600*24*7*argTime))

                if  argTime <=0 and argTime>=-2:
                    sqlStr = sqlStr+' and %s="%s"'%(groupType,yearWeek)

                elif argTime == -3:
                    sqlStr = sqlStr+' and %s<="%s"'%(groupType,yearWeek)
                else:
                    return self._jsonError(460)
            else:

                sqlStr = sqlStr+' and %s="%s"'%(groupType,date)
        elif groupType == "month":
            if date == '0' or date.startswith('-'):
                argTime = int(date)
                realMonth = time.localtime()[1]+argTime or 12
                realYear = time.localtime()[0]
                if realMonth == 12:
                    realYear = time.localtime()[0] - 1
                elif realMonth < 0:
                    realMonth = 12 +argTime + 1
                    realYear = time.localtime()[0] - 1
                realDate = time.strftime("%Y-%m",[realYear, realMonth,0,0,0,0,0,0,0])
                if argTime >= -2 and argTime <= 0:                
                    sqlStr =sqlStr+' and %s="%s"'%(groupType,realDate)
                elif argTime == -3:
                    sqlStr =sqlStr+' and %s<="%s"'%(groupType,realDate)
                else:
                    return self._jsonError(460)

            else:
                sqlStr = sqlStr + ' and %s="%s"'%(groupType,date)
        else:
            return self._jsonError(460)
        sqlStr = sqlStr +'order by lastModify %s limit %s,%s'%(order,start,limit)

        ret = CameraUtils.execCameraSql(sqlStr,None)
        photos= self.formatPhotoRet(order,ret)
        return self._jsonResult({"result":0, "photos":photos})
    
    def Snapshot(self, args, params):
        uid = params.get('uid', None)
        width = params.get('width', 1080)
        height = params.get('height', 720)
        quality = params.get('quality', 100)
        filename = params.get('filename', None)
        
        if not uid:
            return self._jsonError(460)
        if self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)
        if not ProfileFunc.GetBoxDisks():
            return self._jsonError(465)
        if not filename:
            filename = time.strftime("Photo_%Y-%m-%d_%H%M%S", time.localtime()) + ".jpg"
        save_path = self._getSavePath(uid)
        if not os.path.exists(save_path): os.makedirs(save_path)
        filename = save_path + "/" + filename
        try:
            token = self._gettoken()
            result = self.d_obj.camera_get_snapshot(token, uid, int(width), int(height), \
                                    int(quality), filename, dbus_interface=BUS_INTERFACE)
            Log.info("**** Snapshot result = %s"%result)
            if 0 == result:
                self.newSnapShortFile[uid] = False;
                return self._jsonResult()
            else:
                return self._jsonError(528)
        except Exception,e:
            Log.exception("Camera[%s] Snapshot Failed! Reason[%s]"%(uid,e))
            if DBUS_NORLY in str(e):
                UtilFunc.getLogger().exception("Snap Shot kill camera service")
                self._killCameraService()
            return self._jsonError(528)

    def Record(self, args, params):
        uid = params.get('uid', None)
        enable = params.get('enable', 1)
        
        ret = self.Verify(uid)
        if ret: return ret
        self.cameras[uid]['record'] = str(enable)
        Log.info(" ***Record recording cameras[%s], alarm recording cameras [%s]"%(self.recordingCameras, self.alarmRecording))
        if (uid in self.recordingCameras or uid in self.alarmRecording) and 0 == int(enable):
            self._stopRecord(uid, self.cameras[uid]['stream'])
        self._setConfig()
        return self._jsonResult()

    def SyncCameraInfo(self, args, params):
        uid = params.get('uid', None)
        target = params.get('target', None)
        
        if not uid or not target:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        if self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)
        
        try:
            target = json.loads(target)
        except:
            return self._jsonError(460)
        
        for _uid in target:
            if not self.cameras.has_key(_uid):
                continue
            self.cameras[_uid]['week']          = self.cameras[uid]['week']
            self.cameras[_uid]['r1']            = self.cameras[uid]['r1']
            self.cameras[_uid]['r2']            = self.cameras[uid]['r2']
            self.cameras[_uid]['interval']      = self.cameras[uid]['interval']
            self.cameras[_uid]['record']        = self.cameras[uid]['record']
            self.cameras[_uid]['stream']        = self.cameras[uid]['stream']
            self.cameras[_uid]['motiondetect']  = self.cameras[uid]['motiondetect']
            self.cameras[_uid]['sensitive']     = self.cameras[uid]['sensitive']
        self._setConfig()
        return self._jsonResult()

    def ModifyCameraPwd(self, args, params):
        uid = params.get('uid', None)
        oldPassword = params.get('oldPassword', None)
        newPassword = params.get('newPassword', None)
        
        if not uid or not oldPassword or not newPassword:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        
        if oldPassword == newPassword:
            return self._jsonResult()
        
        try:
            ret = self.d_obj.modify_camera_password(uid, oldPassword, newPassword, \
                                                      dbus_interface=BUS_INTERFACE)
            if 0 == ret:
                self.modifyPwd[uid] = {}
                self.modifyPwd[uid]["oldpwd"] = oldPassword
                self.modifyPwd[uid]["newpwd"] = newPassword
                self.recModifyPwdResp[uid] = False
                self.modifyPwdResult[uid] = -1
                self.WaitRecModifyCameraPasswd(uid)
                if(0 == int(self.modifyPwdResult[uid])):
                    return self._jsonResult()
                else:
                    return self._jsonError(529)
            else:
                return self._jsonError(529)
        except Exception, e:
            Log.exception("Camera[%s] SetCameraPwd Failed! Reason[%s]"%(uid,e))
            if DBUS_NORLY in str(e):
                Log.exception("Set Camera password kill camera service")
                self._killCameraService()
            return self._jsonError(528)

    def SetCameraPwd(self, uid, pwd, **params):
        if not uid or not pwd:
            return self._jsonError(460)
        if not self.cameras.has_key(uid):
            return self._jsonError(520)
        pwd = str(pwd)
        
        info = {}
#        if( 0 == cmp(self.cameras[uid]["password"], pwd)):
#            return self._jsonError(Error.SetCameraPasswordSuccess)
        try:
            info["uid"] = uid
            info["password"] = pwd
            self.d_obj.stop_camera_recording(self._gettoken(), uid, int(self.cameras[uid]['stream']), \
                                                      dbus_interface=BUS_INTERFACE)
            result = self.d_obj.set_camera_password(json.dumps(info), dbus_interface=BUS_INTERFACE)
            if 0 ==  result:                 
                if uid in self.recordingCameras:
                    self.recordingCameras.remove(uid)
                if uid in self.alarmRecording:
                    self.alarmRecording.remove(uid)
                self.login[uid]["login"] = True;
                self.cameras[uid]["password"] = pwd
                self._setConfig()
                return self._jsonResult()
            else:
                self.login[uid]["login"] = False;
                return self._jsonError(530)
        except Exception,e:
            Log.exception("Camera[%s] SetCameraPwd Failed! Reason[%s]"%(uid,e))
            if DBUS_NORLY in str(e):
                Log.exception("Set Camera password kill camera service")
                self._killCameraService()
            return self._jsonError(528)

    def playMedia(self, args, params):
        idCode = params.get("idCode", None)
        if not idCode:
            return self._jsonError(460)
        ret = CameraUtils.execCameraSql('select url from fileCache where idCode = ?', (idCode,))
        if not ret:
            raise self._jsonError(464)
        path = ret[0]['url'] 
        mime = mimetypes.guess_type(path)[0]
        return static.serve_file(path, content_type=mime)

    def Verify(self, uid, flag=True):
        if not uid:
            return self._jsonError(460)
        elif not self.cameras.has_key(uid):
            return self._jsonError(520)
        elif self.login.has_key(uid) and self.login[uid].has_key("login") and not self.login[uid]["login"]:
            return self._jsonError(521)
        elif not flag:
            return None
        elif not ProfileFunc.GetBoxDisks():
            return self._jsonError(465)
        elif UtilFunc.isLinuxDiskReadOnly(self.record_path):
            return self._jsonError(527)
    
    def WaitRecNewCameraList(self):
        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            time.sleep(2)
            if self.recNewCamSuc:
                break

    def WaitDbusReport(self, token):
        start_time = time.time()
        report = "Call CameraService Failed"
        while time.time() - start_time < TIMEOUT:
            tiem.sleep(2)
            if self.msgs.has_key(token):
                report = self.msgs[token]
                del self.msgs[token]
                break
            
        return report.lower()
    
    def WaitRecNewSnapShortFile(self, uid):
        start_time = time.time()
        while time.time() - start_time < NEW_SNAP_SHORT_FILE_TIMEOUT:
            time.sleep(1)
            if self.newSnapShortFile[uid]:
                break

    def WaitRecModifyCameraPasswd(self, uid):
        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            time.sleep(2)
            if self.recModifyPwdResp[uid]:
                break

    def _update(self):
        self.intervals = {}
        dayUpdate = False
        today = time.localtime().tm_mday
        Log.info("*** _update start thread !!!")
        while not self.stoped:
            try:
                #UtilFunc.getLogger().info("*** _update thread is live !!!")
                day, hour, min, wday = time.localtime().tm_mday, time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_wday
                if int(hour) == 0 and day != today:
                    dayUpdate = True
                curMins = int(hour) * 60 + int(min)
                for camera in self.cameras.values():
                    if not int(wday) in camera['week']:
                        continue
                    self._checkAutoRecording(curMins, camera, dayUpdate)
                    self._checkAutoSnapshoot(curMins, camera)
                if day != today:
                    today = day
                    dayUpdate = False
                time.sleep(2)
            except Exception,e:
                Log.error("_update Failed! Reason[%s]"%e)
                time.sleep(2)
                continue
    
    def _reConnectCameraThread(self):
        """
        ReConnect camera when camera disconnect or login failed!!!
        """
        Log.info("reConnectCameraThread start !!!")
        while True:
            try:
                hour, min = time.localtime().tm_hour, time.localtime().tm_min
                curMins = int(hour) * 60 + int(min)
                #Log.info("*** _reConnectCameraThread start curMins = %d, self.login.iterkeys() = %s !!!"%(curMins, self.login.iterkeys()))
                for uid in self.login.iterkeys():
                    #Log.info("*** _reConnectCameraThread start uid = %s !!!"%uid)
                    if self.login[uid].has_key('login') and not self.login[uid]['login'] and uid not in self.removeingcameras and self.cameras.has_key(uid):
                        #Log.info("*** _reConnectCameraThread start self.login[uid]['login'] = %d !!!"%self.login[uid]['login'])
                        if self.login[uid].has_key('reconntime') and int(self.login[uid]['reconntime']) == curMins:
                            #Log.info("*** _reConnectCameraThread start self.login[uid].has_key('reconntime') = %d !!!"%self.login[uid].has_key('reconntime'))
                            self._reConnectCamera(uid)
                    elif self.login[uid].has_key('login') and self.login[uid]['login'] and self.login[uid].has_key('relaymode') and self.login[uid]['relaymode'] and uid not in self.removeingcameras and self.cameras.has_key(uid):
                        if self.login[uid].has_key('relayreconntime') and int(self.login[uid]['relayreconntime']) == curMins:
                            self._reConnectCamera(uid)
                time.sleep(5)
            except Exception,e:
                Log.error("_reConnectCameraThread Failed! Reason[%s]"%e)
                time.sleep(5)
                continue
                
    
    def _checkWatchDog(self):
        """
        Watch Dog, check the camera service status.
        """
        camera_is_start = True
        Log.info("*** _checkWatchDog self.stoped : %s!!!"%self.stoped)
        while not self.stoped:
#            UtilFunc.getLogger().info("*** _checkWatchDog thread is live !!!")
            self._cameraWatch(camera_is_start)
            camera_is_start = False
            time.sleep(2)
    
    def _recvStartCSEvent(self):
        """
        Recive watch dog start camera_service singnl method. 
        """
        while True:
            if cs_event.isSet():
                try:
                    self.login = {}
                    self._parseConfig()
                    #self._setScanFolder()
                    self._initRecordData()
                    self._startUpdateThread()
                    self._startReconnectCameraThread()
                    cs_event.clear()
                except Exception ,e:
                    Log.info("*** _recvStartCSEvent is except : %s!!!"%e)
                    time.sleep(5)
                    continue
            else:
                Log.info("*** _recvStartCSEvent is wait !!!")
                cs_event.wait()
    
    def clean(self):
        """
        Clean the records more than 7 days.
        """
        if not ProfileFunc.GetBoxDisks():
            return
        if not self.record_path:
            self.record_path = ProfileFunc.getRecordPath()
            Log.info("*** clean self.record_path : %s!!!"%self.record_path)
        path = os.path.join(self.record_path, SAVE_PATH).replace("\\","/")
        if not os.path.exists(path):
            return
        for ipcam_folder in os.listdir(path):
            dates_folders = os.listdir(os.path.join(path, ipcam_folder))
            dates_folders.sort()
            Log.info("*** clean folder count : %s!!!"%len(dates_folders))
            if len(dates_folders) > self.daystime:
                num = len(dates_folders) - self.daystime
                for i in xrange(num):
                    records_path = os.path.join(path, ipcam_folder, dates_folders[i])
                    UtilFunc.removeDir(records_path)
                    UtilFunc.getLogger().info("Clean Records[%s]"%records_path)
    
    def handleRaiseReply(self, msg): 
        Log.exception("RaiseException returned normally! That's not meant to happen...")
        return
     
    def handleRaiseError(self, msg):
        Log.error("RaiseException raised an exception as expected:[%s]"%str(msg))
        return
    
    def createthumbnail(self, filePath):
        if not os.path.exists(filePath):
            return
        try:
            width = MinWidth
            height = MinHeight
            savePath = ProfileFunc.getSubLibraryPathbyFile(filePath)
            folderPath = os.path.dirname(savePath)
            thumbnail.getThumbNailImage(filePath, MinWidth)
        except Exception, e:
            Log.exception("camera create failed!!! reason [%s]"%e)    
    
    
    
    
    
    
    
     