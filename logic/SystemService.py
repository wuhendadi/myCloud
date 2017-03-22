# -*- coding: utf-8 -*-
#author: ZJW

import os
import json
import types
import cherrypy
import UtilFunc
import Command
import WebFunc
import PopoConfig
import ProfileFunc
import Log
import cherrypy

class System:
    
    exposed = True
    
    def _systemUpgrade(self):
        ret = WebFunc.socketSend('127.0.0.1', 8888, 'upgrade-system')
        if not ret:
            raise cherrypy.HTTPError(462, 'Operation Failed')
        WebFunc.changeStatus()
    
    def _isNeedUpgrade(self):
        ret = WebFunc.socketSend('127.0.0.1', 8888, 'is-need-upgrade')
        if ret:
            ret = ret.split(';')
            res = {'uptodate':UtilFunc.toBoolean(ret[0]) == False, 
                   'version':'',
                   'description':'',
                   'force':ret[1]}
            return WebFunc.jsonResult(res)
        else:
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
    def _isImgUpToDate(self):
        ret = UtilFunc.getIMGVersion()
        return WebFunc.jsonResult({'uptodate':ret['upgrade'] == False, 'version':ret['ver']})
    
    def GET(self, *arg, **params):
#         if intent == 'relay':
#             return WebFunc.jsonResult({'isrelay':UtilFunc.toBoolean(PopoConfig.ISRELAY)})
        if arg and arg[0] == 'update':
            return self._isNeedUpgrade()
        elif arg and arg[0] == 'imgUpdate':
            return self._isImgUpToDate()
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def PUT(self, *arg, **params):       
#         if intent == 'relay':
#             value = UtilFunc.toBoolean(params.get('value', True))
#             PopoConfig.ISRELAY = value
#             if not PopoConfig.setValue('isrelay',value):
#                 raise cherrypy.HTTPError(463, 'Not Permitted')
#             ProfileFunc.getMainServer().status.supplyRelay(value)
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if arg[0] == 'reboot':
            Log.info('Box Restart! Wait later!')
            os.system('reboot')
        elif arg[0] == 'upgrade':
            self._systemUpgrade()
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter') 
        
        cherrypy.response.status = 205
        return
    
    
class Storages:
        
    exposed = True
    
    def _getStorageInfo(self, path):
        ret = {}
        ret['root'] = UtilFunc.toLinuxSlash(path)
        sid = ProfileFunc.getMainServer().diskInfo.get(path,{}).get('id','')
        name = ProfileFunc.getMainServer().diskInfo.get(path,{}).get('name','')
        if sid == '':
            sid, fs, name = Command.getDiskInfo(path)
            ProfileFunc.getMainServer().diskInfo[path] = {'id':sid,'name':name,'fs':fs}
        ret['id'] = sid
        ret['name'] = name
        ret['free'], ret['capacity'] = UtilFunc.getRemainSpace(path)
        if ProfileFunc.isMediaFolder(path): ret['isMediaFolder'] = '1' 
        else: ret['isMediaFolder'] = '0'
        return ret
      
    def GET(self, *arg, **params):
        if arg:
            storageId = arg[0]
            if storageId == 'all':
                files = UtilFunc.getFileList(ProfileFunc.GetBoxDisks(), UtilFunc.getOptParamsInfo(params))
                return WebFunc.jsonResult({'total':len(files),'files':files})
            diskpath = ProfileFunc.getDiskById(storageId)
            if not diskpath:
                raise cherrypy.HTTPError(460, 'Bad Parameters')
            if 'mediaFolders' in arg:
                ret = ProfileFunc.getMainServer().scanFolderMoniter.getMediaFolder(params)
                return WebFunc.jsonResult(ret)
            else:
                return WebFunc.jsonResult(self._getStorageInfo(diskpath))       
        else:
            storages = []
            for disk in ProfileFunc.GetBoxDisks(False):
                storages.append(self._getStorageInfo(disk))
            return WebFunc.jsonResult({'storages':storages, 'status':ProfileFunc.getDiskStatus()})
     
    def POST(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameters')

        storageId = arg[0]
        if not ProfileFunc.GetBoxDisks() or not storageId in ProfileFunc.getStorageIds():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        folders, delpaths = params.get('folders',[]), params.get('except',[])
        if not folders and not delpaths: 
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        folders = UtilFunc.strToList(folders)
        delpaths = UtilFunc.strToList(delpaths)
        ret = ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder(folders,delpaths)
        
        cherrypy.response.status = 205
        return WebFunc.jsonResult(ret)
    
    def DELETE(self, *arg, **params):
        diskId = ''.join(arg)
        try:
            os.system("sync")
            Command.umountDisks(diskId)
                
        except Exception, e:
            Log.error("ShutdownDisk Failed! reason[%s]"%e)
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        cherrypy.response.status = 205
        return 
        
class Version:
    
    exposed = True
    
    def __init__(self):
        self.checkdisks = False 
    
    def GET(self, **params):
        return WebFunc.jsonResult({'deviceType'     : UtilFunc.getDeviceType(),
                                   'serverVersion'  : PopoConfig.VersionInfo,
                                   'system'         :'Linux/PopoBox',
                                   'systemVersion'  : UtilFunc.getSystemVersion(),
                                   'ImgVersion'     : UtilFunc.getIMGVersion()['ver'],
                                   'hardwareVersion': PopoConfig.Hardware,
                                   'ecsVersion'     : ProfileFunc.getMainServer().ecsModule.version() if hasattr(ProfileFunc.getMainServer(), 'ecsModule') else 'NoECS',
                                   })
        
class ESLog:
    
    exposed = True
    
    def __init__(self):
        self.checkdisks = False
    
    def GET(self, *arg, **params):
        LogFolder = Log.getLogDataPath()
        ecsPath   = LogFolder + '/ecs.log'
        esFolder  = LogFolder + '/logs'
        intent = ''.join(arg)
        if intent == 'ecs':
            return WebFunc.DownloadFile(ecsPath)
        elif intent == 'es':
            return WebFunc.DownloadFolderZip(esFolder)
        
        return WebFunc.DownloadFolderZip(LogFolder)
        
