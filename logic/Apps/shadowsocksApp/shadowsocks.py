# -*- coding=utf-8 -*-
#author:ZJW

import os
import cherrypy
import thread
import time
import shadowsocks_manager
import PostStatic
import WebFunc
import UtilFunc
import Log

class ShadowSocks:
    
    exposed = True
    
    def __init__(self):
        self.status    = False
        self.setting   = {}
        self.localIp   = UtilFunc.getLocalIp()
        self.ssm       = shadowsocks_manager.SsManager(self.setting)
        thread.start_new_thread(self._ipWatch, ())
        
    def _ipWatch(self):
        while True:
            localIP = UtilFunc.getLocalIp()
            if localIP != self.localIP and self.ssm.check_state():
                self.ssm.gen_client_conf()
                self.localIp = localIp
            time.sleep(2)
        
    @cherrypy.tools.allow()
    def GET(self, *arg, **params):
        intent = params.get('intent', None)
        if not intent:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        elif intent == 'config':
            conPath = self.ssm.get_client_conf()
            if conPath and os.path.exists(conPath):
                return PostStatic.serve_download(conPath, os.path.basename(conPath))
            else:
                raise cherrypy.HTTPError(464, 'Not Exist')
        elif intent == 'status':
            conPath = self.ssm.get_client_conf()
            lastModify = None
            if conPath and os.path.exists(conPath):
                lastModify = os.path.getmtime(conPath)
            return WebFunc.jsonResult({'status':self.ssm.check_state(),'lastModify':lastModify})
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    @cherrypy.tools.allow()
    def POST(self, *arg, **params):
        return
    
    @cherrypy.tools.allow()
    def PUT(self, *arg, **params):
        intent = params.get('intent', None)
        if not intent:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if intent == 'status':
            value = params.get('value',None)
            if value is None: 
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            if UtilFunc.toBoolean(value):
                if not self.ssm.check_state():  
                    ret = self.ssm.start()
                    if ret != 0:
                        Log.error('Start ShadowSocks Failed! Reason[%s]'%ret)
                        raise cherrypy.HTTPError(462, 'Operation Failed')        
            else:
                if self.ssm.check_state():
                    self.ssm.stop()
                
        cherrypy.response.status = 205
        return 
    
    @cherrypy.tools.allow()
    def DELETE(self, *arg, **params):
        return
    
    