# -*- coding=utf-8 -*-
#author:ZJW

import os
import time
import cherrypy
import thread
import random
import tempfile
import ConfigParser
import shutil
import Command
import WebFunc
import UtilFunc
import popoUpdate
import StartFunc
import ProfileFunc
import PopoConfig
import Log

class AppCtrl:
    
    exposed = True
    
    def __init__(self):
        self.popo_update = popoUpdate.CUpdate()
        self.app_path    = os.path.dirname(os.path.abspath(__file__)).replace('\\','/')
        self.services    = {}
        self.needUpdates = {}
        thread.start_new_thread(self._startAppServices, ())
        thread.start_new_thread(self.updateMonitor, ())
        
    def _getVersion(self, app_name):
        conf_path = self.services[app_name].confPath
        self.cfp  = ConfigParser.ConfigParser()
        self.cfp.read(conf_path)
        version = self.cfp.get('profile', 'version', True, None)
        del self.cfp
        return version
        
    def _isNeedUpdate(self, name):
        appid = 'ElastosServer.' + name
        version = self._getVersion(name)
        version, fileUrl, fileHash = self.popo_update.check(appid, version)
        if version: return True, version
        return False, ''
        
    def _addApp(self, app_name):
        Log.info('App[%s] Start Install!'%app_name)
        ret = self._appUpdate('0.0', app_name)
        if ret:
            self._startAppService(app_name)
        return ret    
          
    def _appUpdate(self, version, name):
        Log.info("App[%s] Start Update!"%name)
        appid = 'ElastosServer.' + name    
            
        version, fileUrl, fileHash = self.popo_update.check(appid, version)
        if version:
            tempData = os.path.join(tempfile.gettempdir(), name+version+'.zip')
            if self.popo_update.download(tempData, fileHash, fileUrl):
                if not os.path.exists(UtilFunc.getBoxUpLockPath() + "/upgrading.lock"):
                    file(UtilFunc.getBoxUpLockPath() + "/upgrading.lock", "wb").close()
                if not self.popo_update.startUpadte(name, tempData):
                    Log.error('APP[%s] Update Failed! Wait Next!'%name)
                    return False
                
                Log.info('APP[%s] Update Complete!'%name)
        else:
            Log.info('App[%s] Need Not Update'%name)

        return True
    
    def _getAppInfo(self,app_name):                       
        ret = {}
        ret['name'] = app_name
        ret['status'] = self.services[app_name].status
        if self.needUpdates.has_key(app_name):
            ret['isNeedUpdate'] = True
            ret['newVersion'] = self.needUpdates[app_name]
        else:
            ret['isNeedUpdate'] = False
            ret['newVersion'] = ''
            
        return ret
        
    def _removeApp(self, app_name):
        app_path = os.path.join(self.app_path, app_name)
        app_service = self.services.pop(app_name)
        if app_service.status == True and hasattr(app_service,'stop'):
            app_service.stop()
        if os.path.exists(app_path):
            shutil.rmtree(app_path)
            del cherrypy.tree.apps[app_service.root]
            
    def _startAppService(self, folder):
        conf_path = os.path.join(self.app_path, folder, 'Config.conf')
        try:
            self.cfp  = ConfigParser.ConfigParser()
            self.cfp.read(conf_path)
            module = self.cfp.get('profile', 'modulename')
            service = self.cfp.get('profile', 'servicename')
            autostart = UtilFunc.toBoolean(self.cfp.get('profile', 'autostart'))
            try:
                apiname = self.cfp.get('profile', 'apiname')
            except:
                apiname = None
            exec("from Apps.%s import %s"%(folder, module))
            exec("appservice = %s.%s()"%(module, service))
            if hasattr(appservice,'start') and autostart:
                appservice.start()
            self.services[folder] = appservice
            appservice.status = True
            appservice.confPath = conf_path
            appservice.root = '/api' + apiname
            if not hasattr(appservice, 'checkdisks'): appservice.checkdisks = False
            if apiname:
                StartFunc.mountService(appservice, appservice.root)
            Log.info('Start App[%s] SuccessFull! BindService[%s]'%(folder, apiname))
        except:
            import traceback
            Log.exception(traceback.format_exc())
            
        del self.cfp
        
    def _changeAppStatus(self, app_name, value):
        app_service = self.services[app_name]
        if app_service.status != value:
            app_service.status = value
            if value and hasattr(app_service,'start'):
                app_service.start()
            elif not value and hasattr(app_service,'stop'): 
                app_service.stop()
    
    def _startAppServices(self):
        Command.setOsEnv('DBUS_SESSION_BUS_ADDRESS')
        for folder in os.listdir(self.app_path):
            if not os.path.isdir(os.path.join(self.app_path, folder)):
                continue
            self._startAppService(folder)
    
    def updateMonitor(self):
        while True:
            try:
                for service in self.services:
                    print service
                    ret , version = self._isNeedUpdate(service)
                    if ret:
                        self.needUpdates.setdefault(service,version)
            except Exception,e:
                Log.exception('updateMonitor Exception! Reason[%s]'%e)
            time.sleep(random.randrange(10,50) * 360)
            
    @cherrypy.tools.allow()   
    def GET(self, *arg, **params):
        app_name = ''.join(arg)
        if not app_name:
            ret = []
            for app_name in self.services.keys():
                ret.append(self._getAppInfo(app_name))
        else:    
            if not self.services.has_key(app_name):
                raise cherrypy.HTTPError(460, 'Bad Parameter')
        
            ret = self._getAppInfo(app_name)
        
        return WebFunc.jsonResult(ret)
    
    @cherrypy.tools.allow() 
    def POST(self, *arg, **params):
        app_name = ''.join(arg)
        if not app_name:
            raise cherrypy.HTTPError(460, 'Bad Parameter') 
        intent = params.get('intent','')
        if intent == 'add':       
            if not self._addApp(app_name):
                raise cherrypy.HTTPError(462, 'Operation Failed')
        elif intent == 'update':
            ret, version = self._isNeedUpdate(app_name)
            if not ret:
                raise cherrypy.HTTPError(463, 'Not Permitted')
            if not self._appUpdate(version, app_name):
                raise cherrypy.HTTPError(462, 'Operation Failed') 
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')  
        
        cherrypy.response.status = 201
        return
    
    @cherrypy.tools.allow() 
    def PUT(self, *arg, **params):
        app_name = ''.join(arg)
        if not app_name: raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not self.services.has_key(app_name):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        intent = params.get('intent','')
        if intent == 'ctrl':
            value = params.get('value','')
            if not value:
                raise cherrypy.HTTPError(460, 'Bad Parameter') 
            value = UtilFunc.toBoolean(value)
            self._changeAppStatus(app_name, value)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        cherrypy.response.status = 205
        return 
    
    @cherrypy.tools.allow() 
    def DELETE(self, *arg, **params):
        app_name = ''.join(arg)
        if not app_name or not self.services.has_key(app_name):
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        return self._removeApp(app_name)
        
        cherrypy.response.status = 205
        return
            
