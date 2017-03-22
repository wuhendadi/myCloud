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
import WebFunc
import ProfileFunc
import thread
import threading
import StartFunc
import thumbnail
import Clog

from Sitelib import libandroidmod
from dbus.mainloop.glib import DBusGMainLoop
from PopoConfig import *

BUS_NAME        = "com.kortide.camera_control_service"
BUS_PATH        = "/com/kortide/camera_control_service"
BUS_INTERFACE   = "com.kortide.camera_control_service.camera_service"
SAVE_PATH       = "CloudMonitor"
CAMERA_TYPE     = {"AUTO" : 0, "ANYKA_3918A1" : 1};
CONFIG_PATH     = "/popoCloudData/IpCam.ini"
DEFAULT_RECORD  = '/mnt/popoCloud'
#CONFIG_PATH     = "d:/IpCam.ini"
RIGHT_REPORT    = "call successfully"
DBUS_NORLY      = "org.freedesktop.DBus.Error.NoReply"
CAMERA_INFO     = ["uid", "type", "ip", "deviceId", "alias", "is_added", "is_live", "is_available",
                 "streams","media_stream_info"]
BIND_INFO       = ["uid", "type", "ip", "deviceId", "alias", "record", "records", "motiondetect",
                 "sensitive","interval","r1","r2","week","stream","islive"]
CAMERA_APP      = os.path.dirname(os.path.abspath(__file__)) + "/camera-service"
TIMEOUT         = 20
MAXMINUTES      = 24 * 60
MINMINUTES      = 0
SEND_ALARM_TIME = 20 * 60
DISK_ALARM_TIME = 12 * 60 * 60
KILL_CS_TIME    = 5 * 60
ALARM_TYPE      = type('Enum', (), {"CAMERA_ALARM": 1, "lOWSPACE_ALARM": 2, "FULLSPACE_ALARM": 3})
SPACE_TYPE      = type('Enum', (), {"LOW_SPACE": 500 * 1024, "FULL_SPACE": 100 * 1024})
ALARM_STATUS    = type('Enum', (), {"ALARM_ON": 1, "ALARM_OFF": 0})
lock_serach     = threading.Lock()
cs_event        = threading.Event() #start camera service event
NEW_SNAP_SHORT_FILE_TIMEOUT = 5
#UtilFunc.setCmaeraFolder(SAVE_PATH)

def startCameraService():
    Clog.info("Start Camera-Service!")
    s = libandroidmod.execute_shell("ps | grep "+ CAMERA_APP)
    if s : os.system("busybox killall -9 camera-service")
    os.system("chmod 777 "+ CAMERA_APP)
    os.system(CAMERA_APP+" /popoCloudData/camera.ini &")
    time.sleep(2)    

def killCameraService():
    Clog.info("Kill Camera-Service!")
    s = libandroidmod.execute_shell("ps | grep "+ CAMERA_APP)
    if s : os.system("busybox killall -9 camera-service")

class CameraCtrl:
    
    exposed = True
    
    def __init__(self):
        DBusGMainLoop(set_as_default=True)
        self.cameras          = {}
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
        self.recordingCameras = []
        self.alarmRecording   = []
        self.alarmRecordTime  = {}
        self.newSnapShortFile = {}
        self.stoped           = False
        self.recNewCamSuc     = False
        self.record_path      = None
        #self._setScanFolder()
        self._parseConfig()
        thread.start_new_thread(self._update, ())
        thread.start_new_thread(self._checkWatchDog, ())
        Clog.info("**** CameraCtrl init ****")
        
    def _initDbusSession(self):
        try:
            self.d_obj = self._getRmoteObject()
            self.iface = self._getInterFace()
            self._addAllSignalReceiver()
            self._startMessageLoop()
        except Exception, e:
            Clog.error("_initDbusSession Failed! Reason[%s]"%e)
            return
        cs_event.set()
        
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
            Clog.info("Camera-Service Haven't Existed! Start it!")
            startCameraService()
            self.killCstime = time.time()
            self._initDbusSession()
    
    def _initRecordData(self):
        if self.recordingCameras:
            self.recordingCameras = []
        if self.alarmRecording:
            self.alarmRecording = []
    
    def _getRecordTime(self, bt, et):
        bt, et = int(bt), int(et)
        if et < bt or et == bt:
            return [x for x in xrange(MINMINUTES,MAXMINUTES) if x >= bt or x < et]
        else:
            return [x for x in xrange(MINMINUTES,MAXMINUTES) if x >= bt and x < et] 
                 
    def _checkAutoRecording(self, min, camera, dayUpdate=False):
        if str(camera['record']) == '0':
            if camera["uid"] in self.recordingCameras:
                self._record(camera["uid"], camera['stream'],0)
            return
        if self._checkFullDiskSpace(camera["uid"], SPACE_TYPE.LOW_SPACE):
            Clog.info("camera[%s] Low Space to Stop Recording at [%s]"%(camera["uid"], str(min)))
            self._record(camera["uid"], camera['stream'], 0)
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
        if min in recording_times and not camera["uid"] in self.recordingCameras and not camera["uid"] in self.alarmRecording:
            self._record(camera["uid"], camera['stream'], 1)
            Clog.info("camera[%s] Start Recording at [%s]"%(camera["uid"], str(min)))
        elif not min in recording_times and camera["uid"] in self.recordingCameras and not camera["uid"] in self.alarmRecording:
            self._record(camera["uid"], camera['stream'], 0)
            Clog.info("camera[%s] Stop Recording at [%s]"%(camera["uid"], str(min)))
        elif dayUpdate and (camera["uid"] in self.recordingCameras or camera["uid"] in self.alarmRecording):
            self._record(camera["uid"], camera['stream'], 0)
            Clog.info("camera[%s] Stop Recording at [%s] update day..."%(camera["uid"], str(min)))
        elif camera["uid"] in self.alarmRecording and self.alarmRecordTime.has_key(camera["uid"]):
            hour, min = time.localtime().tm_hour, time.localtime().tm_min
            cur_mins = int(hour) * 60 + int(min)
            if cur_mins >= self.alarmRecordTime[camera["uid"]]:
                result = self._stopAlarmRecording(camera["uid"])
    
    def _checkAutoSnapshoot(self, min, camera):
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
                self.snapshot(camera["uid"],{})
                self.intervals[camera["uid"]] = time.time()
        
    def _getAlarmRecordingTime(self):    
        hour, min = time.localtime().tm_hour, time.localtime().tm_min
        start_mins = int(hour) * 60 + int(min)
        end_mins = start_mins + 20
        if end_mins > MAXMINUTES-1:
            end_mins = end_mins - MAXMINUTES
        return start_mins, end_mins
    
    def _startAlarmRecording(self, uid, end_mins):
        if not self.cameras:
            return False
        if not self.cameras.has_key(uid):
            return False
        filename = ".tmp_Warning_%Y-%m-%d_%H%M%S"
        self._record(uid, self.cameras[uid]['stream'],1)
        Clog.info("******* _startAlarmRecording, result = %s ********"%result)
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
        Clog.info("******* _stopAlarmRecording, result = %s ********"%result)
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
        Clog.info("******* alarm Recording  !!! ********")    
        start_mins, end_mins = self._getAlarmRecordingTime()
        self.alarmRecordTime[uid] = end_mins        
        self._startAlarmRecording(uid, end_mins)
  
    def _checkFullDiskSpace(self, uid, lowspace=0):
        if not ProfileFunc.GetBoxDisks() or not uid or not self.cameras.has_key(uid):
            return True
        if not self.record_path:
            self.record_path = DEFAULT_RECORD
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
        Clog.info("********** _sendAlarmMsg **********!!!")
        if int(self.alarmStatus) == ALARM_STATUS.ALARM_OFF:
            Clog.info("the alarm status is off !!!")
            return
        if not uid or not type or not self.cameras or not self.cameras.has_key(uid):
            return
        if not self.emails and not self.mobiles:
            return
        if type == ALARM_TYPE.CAMERA_ALARM:
            if not imagePath or not os.path.exists(imagePath):
                Clog.info("********** imagePath not exists...[%s]"%imagePath)
                return
            if self.cameras[uid]['alias']:
                cameraName = self.cameras[uid]['alias']
            else:
                cameraName = self.cameras[uid]['uid']
            createShare = {}
            createShare = json.loads(UtilFunc.createShare(imagePath, 15, False))
            if createShare and createShare.has_key('url'):
                shareLink = createShare['url']
                Clog.info("on new alarm report sharelink = [%s]!!!"%shareLink)
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
        Clog.info("*** _sendAlarmMsg get hub ret: %s" % ret) 
        if ret['result'] != 0:
            Clog.info("Send AlarmReport Failed! Reason[%s]" % ret['message']) 
        else:
            Clog.info("Send AlarmReport SuccessFull!")
        
    def _syncCameraInfo(self, item):
        try:          
            if int(item['uid']) < 0: return
            if not self.cameras.has_key(str(item['uid'])):
                self._initCameraInfo(str(item['uid']), item['type'], item['deviceId'], item['ip'], item['alias'])
            else:
                self.cameras[str(item['uid'])]['islive'] = str(item['is_live'])
                self.cameras[str(item['uid'])]['type'] = item['type']
                self.cameras[str(item['uid'])]['ip'] = item['ip']
                self.cameras[str(item['uid'])]['width'] = item['media_stream_info'][1][2][3]
                self.cameras[str(item['uid'])]['height'] = item['media_stream_info'][1][2][4]
            self._setConfig()
            Clog.exception("Sync Camera Info SuccessFull!")
        except Exception, e:
            Clog.exception("Sync Camera Info Failed!Reason[%s]"%e)
    
    def _killCameraService(self):
        Clog.info("*******_killCameraService********")
        curTime = time.time()
        if curTime - self.killCstime > KILL_CS_TIME:
            killCameraService()
            self.killCstime = time.time()
        else:
            return
    
    def start(self):
        Clog.info("*** start self.stoped : %s!!!"%self.stoped)
        self.stoped = False
    
    def stop(self):
        Clog.info("*** stop self.stoped : %s!!!"%self.stoped)
        self.stoped = True
        time.sleep(2)
        os.system("killall -9 camera-service")
        Clog.info('Camera-Service Killed!')
        
    def onNewCameraList(self, cameras, **params):
        Clog.info("************** on New camera list ***************")
        Clog.info("***** cameras : [%s]"%cameras)
        lock_serach.acquire()
        self.search_list = []
        self.recNewCamSuc = False
        values = self.cameras.values()
        for camera in cameras:
            cameraInfo = {CAMERA_INFO[i]:camera[i] for i in xrange(len(CAMERA_INFO))}
            self.search_list.append(cameraInfo)
            self._syncCameraInfo(cameraInfo)
        self.recNewCamSuc = True
        lock_serach.release()

    def onNewCameraInfo(self, camera, **params):
        Clog.info("Received New CameraInfo")
        cameraInfo = {CAMERA_INFO[i]:camera[i] for i in xrange(len(CAMERA_INFO))}
        self._syncCameraInfo(cameraInfo)
    
    def onNewCameraNetworkInfo(self, netinfo, **params):
        Clog.info("Received New NetWorkInfo")
        return
    
    def onNewCameraSensorIspInfo(self, ispinfo, **params):
        Clog.info("Received New IspInfo")
        return
    
    def onHLSStart(self, uid, streamid, hlspath, **params):
        Clog.info("Camera[%s] start Playing!"%uid)
        return
    
    def onHLSStop(self, uid, streamid, **params):
        Clog.info("Camera[%s] Stop HLS Play!"%uid)
        return
    
    def onNewRecordingFile(self, uid, streamid, filename, **params):
        Clog.info("*** onNewRecordingFile Camera[%s] Recording[%s]!"%(uid, filename))
        newfile = filename.replace(".tmp_", "")
        os.rename(filename, newfile)
        Clog.info("Camera[%s] NewRecordingFile Recording[%s] Completed!"%(uid, newfile))
        if UtilFunc.isLowDiskSpace(self.record_path, 120 * len(self.cameras.keys()) * 1024):
            self._record(uid, streamid, 0)
            Clog.warning("Disk Not Enough Space! Change Disk Please!")
        self.createthumbnail(newfile, 'video')
    
    def onRecordingStop(self, uid, streamid, **params):
        Clog.info("Camera[%s] Stop Recording!"%uid)
        return

    def onNewSnapshotFile(self, uid, filename, **params):
        Clog.info("Camera[%s] Take New Photo[%s]!"%(uid, filename))
        self.newSnapShortFile[uid] = True;
        self.createthumbnail(filename, 'picture')
        return
    
    def onNewAlarmReport(self, uid, msg, arg, **params):
        uid = str(uid)
        Clog.warning("Receive an AlarmReport By Camera[%s]!"%uid)
        if not self.cameras or not self.cameras.has_key(uid):
            Clog.info("Camera is not bind !!!")
            return 
        if str(self.cameras[uid]["motiondetect"]) != "1":
            Clog.info("Camera motiondetect is off !!!")
            return
        
        if self._checkFullDiskSpace(uid, SPACE_TYPE.LOW_SPACE):
            Clog.info("Alarminfo has no disk space!!!")
            return
        if self.alarmtime.has_key(uid) and (time.time() - self.alarmtime.get(uid, 0)) < SEND_ALARM_TIME:
            return
        self.alarmtime[uid] = time.time() 
        
        name=time.strftime("Warning_%Y-%m-%d_%H%M%S", time.localtime()) + ".jpg"
        self.snapshot(uid, {'filename':name})
        save_path = self._getSavePath(uid)
        imagePath = save_path + "/" + name
        type = ALARM_TYPE.CAMERA_ALARM 
        self.WaitRecNewSnapShortFile(uid)
        self._sendAlarmMsg(uid, type, imagePath)
        self._alarmRecording(uid)

    
    def onNewAsyncCallResponse(self, token, uid, stream_id, method_name, error_code, text_info):
        Clog.info("receive one async respose with Token[%s]" % token)
        self.msgs[token] = text_info
        return
    
    
    def _setConfig(self):
        cf = ConfigParser.ConfigParser()
        cf.add_section('profile')
        cf.set("profile", "daystime",   str(self.daystime))
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
            Clog.exception("_getConfigOption Failed! Reason[%s]"%e)
            return ''
    
    def _parseConfig(self):
        if not os.path.exists(CONFIG_PATH):
            self._setConfig()
        else:
            try:
                cf = ConfigParser.ConfigParser()
                cf.read(CONFIG_PATH)
                self.daystime       = int(self._getConfigOption(cf, "profile", "daystime"))
                self.record_path    = DEFAULT_RECORD
                self.mobiles        = self._getConfigOption(cf, "profile", "mobiles")
                self.emails         = self._getConfigOption(cf, "profile", "emails")
                self.alarmStatus    = self._getConfigOption(cf, "profile", "alarmStatus")
                for section in cf.sections():
                    if section == 'profile': continue
                    item = {key:self._getConfigOption(cf, section, key) for key in BIND_INFO}
                    item['uid'] = str(item['uid'])
                    self._initCameraInfo(item['uid'], camera = item)
                    #self.syncCameras(camera['uid'], camera)
                Clog.info("parseConfig SuccessFull!")  
            except Exception,e:
                Clog.exception("parseConfig Failed! Reason[%s]"%e)
                self._setConfig()

    
    def _getRmoteObject(self):
        return dbus.SessionBus().get_object(BUS_NAME, BUS_PATH)
        
    def _getInterFace(self):
        return dbus.Interface(self.d_obj, BUS_INTERFACE)    
        
    def _gettoken(self):
        current_token = self.token
        self.token += 1
        return current_token
        
    def _getSavePath(self, uid, alias=None):
        folder = time.strftime("%Y-%m-%d", time.localtime())
        if not uid: return None
        if not ProfileFunc.GetBoxDisks(): return None
        if not self.record_path: self.record_path = DEFAULT_RECORD
        name = uid
        record_path = os.path.join(self.record_path, SAVE_PATH)
        save_path = os.path.join(record_path, name, folder).replace("\\", "/")
        return save_path
    
    def _setScanFolder(self):
        disks = ProfileFunc.GetBoxDisks()
        if not disks: return
        scan_path = os.path.join(disks[0], SAVE_PATH)
        if not os.path.exists(scan_path): os.makedirs(scan_path)
        needscanfolders = ProfileFunc.getMainServer().scanFolderMoniter.getMediaFolder({'folder':disks[0]})
        if needscanfolders and not scan_path in needscanfolders:
            ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder([{'folder':scan_path,'type':'all'}],[])               
    
    def _jsonResult(self, ret=None):
        return WebFunc.jsonResult(ret)
    
    def _jsonError(self, errMsg):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return UtilFunc.callBack(UtilFunc.makeError(errMsg))
    
    def _initCameraInfo(self, uid, type='', devId='', ip='', alias='', camera={}):
        Clog.info("initCamera uid:[%s]"%uid)
        if not uid: return
        if not camera:
            self.cameras[uid] = {"uid"         :uid,
                                "type"         :type,
                                "deviceId"     :devId,
                                "ip"           :ip,
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
                                "width"        :1280,
                                "height"       :720}
        else:
            if not self.cameras or not self.cameras.has_key(uid):
                self.cameras[uid] = camera
            else:
                for key in self.cameras[uid].keys():
                    if camera.has_key(key):
                        self.cameras[uid][key] = camera[key]
                        
    def _record(self, uid, stream=1, enable=1, isAlarm=False):
        if not ProfileFunc.GetBoxDisks():
            return False
        if UtilFunc.isLowDiskSpace(self.record_path, 120 * len(self.cameras.keys()) * 1024):
            Clog.info("Disk Haven't Enough Space For Recording! Please Clean it!")
            return False
        save_path = self._getSavePath(uid)
        if not os.path.exists(save_path): os.makedirs(save_path)
        if self.cameras[uid]['records'] != save_path:
            self.cameras[uid]['records'] = save_path
            self._setConfig()
        try:
            self.setRecordConfig(int(uid), int(stream), self._getSavePath(uid,self.cameras[uid]['alias']))
            self.d_obj.camera_enable_record(self._gettoken(), int(uid), int(stream), dbus.Boolean(int(enable)), \
                                                   dbus_interface=BUS_INTERFACE)
            Clog.info("Camera[%s] ChangeRecording Status! Values[%s]"%(uid,enable))
            if int(enable) == 0 and uid in self.recordingCameras:
                self.recordingCameras.remove(uid)
            elif int(enable) == 1 and not uid in self.recordingCameras:
                self.recordingCameras.append(uid) 
        except Exception,e:
            Clog.exception("Camera[%s] start Recording Failed! Reason[%s]"%(uid,e))
            if isAlarm and uid in self.alarmRecording:
                self.alarmRecording.remove(uid)
            
            return False
        
        if isAlarm:
            if not uid in self.alarmRecording:
                self.alarmRecording.append(uid)
                
        return True
        
    def search(self, camera={}):
        Clog.info("************** Search Camera***************")
        ip = camera.get('ip', '')
        netmask = camera.get('netmask', '')
        try:
            self.d_obj.scan_cameras(self._gettoken(), ip, netmask, dbus_interface=BUS_INTERFACE)
            self.WaitRecNewCameraList()
            Clog.info("Finded Cameras: [%s]"%self.search_list)
            return self._jsonResult({"data":self.search_list})
        except Exception,e:
            Clog.exception("Search Cameras Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')

    def _getSearchResultByIp(self, cameras=[], lists=[]):
        search_list = []
        if not cameras or not lists:
            return search_list
        for camera in cameras:
            for list in lists:
                if camera['ip'] == list['ip']:
                    if not list['uid']:
                        list['uid'] = camera['uid']
                    search_list.append(list)
        return search_list

    def getInfo(self, uid):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not self.cameras.has_key(uid):
            raise cherrypy.HTTPError(463, 'Not Permitted')

        return self._jsonResult({'data':self.cameras[uid]})
    
    
    def add(self, camera):
        Clog.info("************** Add Camera***************")
        devId = camera.get('deviceId',None)
        if not devId: raise cherrypy.HTTPError(460, 'Bad Parameter')
        type = int(camera.get('type', 0))
        ip = camera.get('ip', 0)
        account = camera.get('account', '')
        pwd = camera.get('password', '')
        alias = camera.get('alias', '')
        try:
            uid = self.d_obj.add_camera(self._gettoken(), type, ip, devId, account, pwd, \
                                           alias, dbus_interface=BUS_INTERFACE)
            if uid >= 0:
                self._initCameraInfo(str(uid), str(type), devId, ip, alias)
                self._setConfig()
                Clog.info("AddCamera [%s] SuccessFull! uid[%s]"%(devId,uid))
                return self._jsonResult({"info":self.cameras[str(uid)]})
            else:
                Clog.info("AddCamera [%s] Refuse! Reason[%s]"%(devId,uid))
                raise cherrypy.HTTPError(463, 'Not Permitted')
        except Exception,e:
            Clog.info("AddCamera [%s] Failed! Reason[%s]"%(devId,e))
            raise cherrypy.HTTPError(462, 'Operation Failed')
    
    def Remove(self, uid):
        self.Verify(uid)
        try:
            Clog.info("************** Remove Camera ************** ")
            if uid in self.recordingCameras or uid in self.alarmRecording: 
                self._record(uid, self.cameras[uid]['stream'], 0)
            self.d_obj.del_camera(self._gettoken(), int(uid), dbus_interface=BUS_INTERFACE)
            obj = self.cameras.pop(uid)
            if self.alarmtime.has_key(uid): del self.alarmtime[uid]
            if self.diskALarmTime.has_key(uid): del self.diskALarmTime[uid]
            if self.intervals.has_key(uid): del self.intervals[uid]
            if self.alarmRecordTime.has_key(uid): del self.alarmRecordTime[uid]
            self._setConfig()
                
        except Exception,e:
            Clog.exception('Remove Failed! Reason[%s]'%e)
            if DBUS_NORLY in str(e):
                Clog.exception("Remove kill camera service")
                self._killCameraService()
            raise cherrypy.HTTPError(462, 'Operation Failed')
    
    def list(self):
        Clog.info("************** List Cameras **************")
        self.search()
        return self._jsonResult(self.cameras.values())
    
    def rename(self, uid, alias):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        elif not self.cameras.has_key(uid):
            raise cherrypy.HTTPError(463, 'Not Permitted')
        old_name = self.cameras[uid]["alias"]
        if old_name == alias:
            return
        self.cameras[uid]["alias"] = alias
        return
    
    def setRecordConfig(self, uid, streamid, path="", filename=".tmp_Record_%Y-%m-%d_%H%M%S", duration=1200, **params):
        if not path: path = self._getSavePath(uid)
        self.d_obj.set_camera_recording_config(self._gettoken(), int(uid), int(streamid), path, filename, \
                                               int(duration), dbus_interface=BUS_INTERFACE)
        if self.cameras.has_key(uid):
            self.cameras[uid]["records"] = path
            self.cameras[uid]["stream"] = streamid
            self._setConfig()
        Clog.info("Camera[%s] SetRecordConfig SuccessFull!"%uid)
      
    def setInterval(self, uid, interval=30):
        self.Verify(uid)
        if not self.record_path:
            self.record_path = DEFAULT_RECORD
        Clog.info("*** setInterval self.record_path : %s!!!"%self.record_path)
        if UtilFunc.isLowDiskSpace(self.record_path, 100 * 1024):
            raise cherrypy.HTTPError(467, 'Not Enough Space')
        if int(interval) < 0:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        self.cameras[uid]["interval"] = str(interval)
        self.intervals[uid] = time.time()
        self._setConfig()
        self.snapshot(uid,{})
        return
    
    def setMobile(self, mobiles):
        try:
            if isinstance(mobiles, types.StringType):
                mobiles = json.loads(mobiles)
            self.mobiles = mobiles
        except Exception,e:
            Clog.exception('SetMobile Failed! Reason[%s]'%e)
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        self._setConfig()
        return
    
    def getMobiles(self):
        return self._jsonResult({'mobiles':self.mobiles})
    
    def setEmail(self, emails):
        try:
            if isinstance(emails, types.StringType):
                emails = json.loads(emails)
            self.emails = emails
        except Exception,e:
            Clog.exception('SetEmail Failed! Reason[%s]'%e)
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        self._setConfig()
        return
    
    def getEmails(self):
        return self._jsonResult({'emails':self.emails})
    
    def setAlarmInfo(self, alarmInfo):
        if not alarmInfo:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        try:
            if isinstance(alarmInfo, types.StringType):
                self.alarminfo = json.loads(alarmInfo)
            else:
                self.alarminfo = alarmInfo
        except Exception,e:
            Clog.exception('SetAlarmInfo Failed! Reason[%s]'%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
        self._setConfig()
        return self._jsonResult()
    
    def getAlarmInfo(self):
        return self._jsonResult({'alarminfo':self.alarminfo})
    
    def setAlarmStatus(self, status=1):
        if int(status) == ALARM_STATUS.ALARM_OFF:
            self.alarmStatus = ALARM_STATUS.ALARM_OFF
        elif int(status) == ALARM_STATUS.ALARM_ON:
            self.alarmStatus = ALARM_STATUS.ALARM_ON
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        self._setConfig()
        return
    
    def getAlarmStatus(self):
        return self._jsonResult({'alarmstatus':self.alarmStatus})

    def setRegular(self, uid, params):
        self.Verify(uid)
        fi = params.get('fi',[540,1080])
        se = params.get('se',[])
        week = params.get('week',[0,1,2,3,4])
        if not self.record_path:
            self.record_path = DEFAULT_RECORD
            Clog.info("*** SetRegular self.record_path : %s!!!"%self.record_path)
        Clog.info("**********SetRegular*****  len keys : %d"%len(self.cameras.keys()))
        if UtilFunc.isLowDiskSpace(self.record_path, 120 * len(self.cameras.keys()) * 1024):
            raise cherrypy.HTTPError(467, 'Not Enough Space')
        camera = self.cameras[uid]
        try:
            camera["r1"]    = fi
            camera["r2"]    = se
            camera['week']  = week
        except Exception,e:
            Clog.exception('Json Loads Failed! Reason[%s]'%e)
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if uid in self.recordingCameras or uid in self.alarmRecording:
            self._record(uid, self.cameras[uid]['stream'],0)
        self._setConfig()
        return
    
    def setMotionDetect(self, uid, params):
        #set Warning Report
        self.Verify(uid)
        enable = int(params.get('enable', 1))
        sensitive = int(params.get('sensitive', 1))
        if sensitive > 100 or sensitive < 0:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not self.record_path: self.record_path = DEFAULT_RECORD
        if UtilFunc.isLowDiskSpace(self.record_path, 100 * 1024) and enable == 1:
            raise cherrypy.HTTPError(467, 'Not Enough Space')
        try:
            Clog.info("**********SetMotionDetect**********")
            self.d_obj.camera_enable_motion_detect(self._gettoken(), int(uid), dbus.Boolean(enable), \
                                    int(sensitive), dbus_interface=BUS_INTERFACE)
            self.cameras[uid]["motiondetect"] = str(enable)
            self.cameras[uid]["sensitive"] = str(sensitive)
            return
        except Exception,e:
            Clog.exception("SetMotiondetect Failed! Reason[%s]"%e)
            if DBUS_NORLY in str(e):
                Clog.exception("Set Motiondetect kill camera service")
                self._killCameraService()
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
    def setResolution(self, uid, params):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        streamId = int(params.get('streamId', 1))
        width = int(params.get('width', 1280))
        height = int(params.get('height', 720))
        try:
            self.d_obj.set_camera_video_resolution(self._gettoken(), int(uid), streamId, width, height, dbus_interface=BUS_INTERFACE)
            Clog.info("Camera[%s] setResolution To [%s * %s]"%(uid, width, height))
        except Exception,e:
            Clog.info("Camera[%s] setResolution To Failed！ Reason[%s]"%(uid,e))
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
    def setPTZCtrl(self, uid, params):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        op = params.get('option', 0)
        speed = params.get('speed', 99)
        end = params.get('end', None)
        if int(op) != 0 and not end:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        try:
            self.d_obj.do_camera_ptz_control(self._gettoken(), int(uid), op, speed, int(end), dbus_interface=BUS_INTERFACE)
            Clog.info("Camera[%s] setPTZ To [%s]"%(uid,end))
        except Exception,e:
            Clog.info("Camera[%s] setPTZ To Failed！ Reason[%s]"%(uid,e))
            raise cherrypy.HTTPError(462, 'Operation Failed')

    def records(self, name=None):
        if not name:
            parent_path = os.path.join(self.record_path, SAVE_PATH)
            return self._jsonResult({"folders":UtilFunc.getFileList(parent_path)})
        else:
            path = os.path.join(self.record_path, SAVE_PATH, name)
        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')
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
        return self._jsonResult({"folders":tmp_list})
    
    def snapshot(self, uid, params):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        width = int(params.get('width', 1080))
        height = int(params.get('height', 720))
        quality = int(params.get('quality', 100))
        filename = params.get('filename',None)
        if not filename:
            filename = time.strftime("Photo_%Y-%m-%d_%H%M%S", time.localtime()) + ".jpg"
        save_path = self._getSavePath(uid)
        if not os.path.exists(save_path): os.makedirs(save_path)
        filename = save_path + "/" + filename
        try:
            self.d_obj.camera_get_snapshot(self._gettoken(), int(uid), int(width), int(height), \
                                    int(quality), filename, dbus_interface=BUS_INTERFACE)
            self.newSnapShortFile[uid] = False;
            Clog.info("Camera[%s] Take Snapshot:[%s]"%(uid,filename))
        except Exception,e:
            Clog.exception("Camera[%s] Snapshot Failed! Reason[%s]"%(uid,e))
#             if DBUS_NORLY in str(e):
#                 Clog.exception("Snapshot kill camera service")
#                 self._killCameraService()
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
#     def SyncCameraInfo(self, uid, target):
#         if not uid or not target:
#             raise cherrypy.HTTPError(460, 'Bad Parameter')
#         if not self.cameras.has_key(uid):
#             raise cherrypy.HTTPError(463, 'Not Permitted')
#         try:
#             target = json.loads(target)
#         except:
#             raise cherrypy.HTTPError(460, 'Bad Parameter')
#         
#         for _uid in target:
#             if not self.cameras.has_key(_uid):
#                 continue
#             self.cameras[_uid]['week']          = self.cameras[uid]['week']
#             self.cameras[_uid]['r1']            = self.cameras[uid]['r1']
#             self.cameras[_uid]['r2']            = self.cameras[uid]['r2']
#             self.cameras[_uid]['interval']      = self.cameras[uid]['interval']
#             self.cameras[_uid]['record']        = self.cameras[uid]['record']
#             self.cameras[_uid]['stream']        = self.cameras[uid]['stream']
#             self.cameras[_uid]['motiondetect']  = self.cameras[uid]['motiondetect']
#             self.cameras[_uid]['sensitive']     = self.cameras[uid]['sensitive']
#         self._setConfig()
#         return self._jsonResult()
        
        
    def Verify(self, uid, flag=True):
        if not uid:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        elif not self.cameras.has_key(uid):
            raise cherrypy.HTTPError(463, 'Not Permitted')
        elif not flag:
            return None
        elif not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disks')
        elif UtilFunc.isLinuxDiskReadOnly(self.record_path):
            raise cherrypy.HTTPError(463, 'Not Permitted')
        
        return None
    
    def WaitRecNewCameraList(self):
        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            time.sleep(0.5)
            if self.recNewCamSuc:
                break

    def WaitDbusReport(self, token):
        start_time = time.time()
        report = "Call CameraService Failed"
        while time.time() - start_time < TIMEOUT:
            time.sleep(2)
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
            
    def _update(self):
        self.intervals = {}
        dayUpdate = False
        today = time.localtime().tm_mday
        Clog.info("*** _update start thread !!!")
        while not self.stoped:
            try:
                day, hour, min, wday = time.localtime().tm_mday, time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_wday
                if int(hour) == 0 and day != today:
                    Clog.info("*** change today day = %s, today = %s!!!"%(day, today))
                    dayUpdate = True
                curMins = int(hour) * 60 + int(min)
                for camera in self.cameras.values():
                    if not int(wday) in camera['week']:
                        if camera['uid'] in self.recordingCameras:
                            self._record(camera['uid'], camera['stream'], 0)
                        continue
                    self._checkAutoRecording(curMins, camera, dayUpdate)
                    self._checkAutoSnapshoot(curMins, camera)
                if day != today:
                    today = day
                    dayUpdate = False
                time.sleep(2)
            except Exception,e:
                import traceback
                Clog.exception(traceback.format_exc())
                time.sleep(2)
                continue
    
    def _checkWatchDog(self):
        camera_is_start = True
        Clog.info("*** _checkWatchDog self.stoped : %s!!!"%self.stoped)
        while not self.stoped:
            self._cameraWatch(camera_is_start)
            camera_is_start = False
            time.sleep(2)
    
    def clean(self):
        if not ProfileFunc.GetBoxDisks():
            return
        if not self.record_path:
            self.record_path = DEFAULT_RECORD
            Clog.info("*** clean self.record_path : %s!!!"%self.record_path)
        path = os.path.join(self.record_path, SAVE_PATH).replace("\\","/")
        if not os.path.exists(path):
            return
        for ipcam_folder in os.listdir(path):
            dates_folders = os.listdir(os.path.join(path, ipcam_folder))
            dates_folders.sort()
            Clog.info("*** clean folder count : %s!!!"%len(dates_folders))
            if len(dates_folders) > self.daystime:
                num = len(dates_folders) - self.daystime
                for i in xrange(num):
                    records_path = os.path.join(path, ipcam_folder, dates_folders[i])
                    UtilFunc.removeDir(records_path)
                    Clog.info("Clean Records[%s]"%records_path)
        Clog.clean()
    
    def createthumbnail(self, filePath, fileType):
        if not os.path.exists(filePath):
            return
        savePath = ProfileFunc.getSubLibraryPathbyFile(filePath)
        thumbnail.getOrCreateThumb(filePath, savePath, fileType)

    def GET(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disks')
        intent = arg[0]
        if intent == 'info':
            return self.getInfo(''.join(arg[1:]))
        elif intent == 'list':
            return self.list()
        elif intent == 'search':
            return self.search(params.get('cameras',{}))
        elif intent == 'records':
            return self.records(params.get('name',None))
        elif intent == 'mobiles':
            return self.getMobiles()
        elif intent == 'emails':
            return self.getEmails()
        elif intent == 'alarmstatus':
            return self.getAlarmStatus()
        elif intent == 'alarminfo':
            return self.getAlarmInfo()
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def POST(self, *arg, **params):
        if not arg or len(arg) < 2:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disks')
        intent,uid = arg[0],arg[1]
        if intent == 'snapshot':
            return self.snapshot(uid, params)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')

    
    def PUT(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disks')
        intent, uid = arg[0], ''.join(arg[1:])
        if intent == 'add':
            return self.add(params.get('camera',{}))
        elif intent == 'rename':
            self.rename(uid,params.get('alias',''))
        elif intent == 'interval':
            self.setInterval(uid, params.get('interval',30))
        elif intent == 'mobiles':
            self.setMobile(params.get('mobiles', None))
        elif intent == 'emails':
            self.setEmail(params.get('emails', None))
        elif intent == 'alarminfo':
            self.setAlarmInfo(params.get('alarminfo',None))
        elif intent == 'alarmstatus':
            self.setAlarmStatus(params.get('alarmstatus',None))
        elif intent == 'regular':
            self.setRegular(uid, params)
        elif intent == 'motionDetect':
            self.setMotionDetect(uid, params)
        elif intent == 'ptzctrl':
            self.setPTZCtrl(uid,params)
        elif intent == 'resolution':
            self.setResolution(uid,params)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        cherrypy.response.status = 205
        return
    
    def DELETE(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        self.Remove(''.join(arg))
        cherrypy.response.status = 205
        return 


