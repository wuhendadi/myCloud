# -*- coding=utf-8 -*-
#author:ZJW

import os
import cherrypy
import thread
import time
import openvpn_manager
import PostStatic
import WebFunc
import UtilFunc
import Log

class NetSurf:
    
    exposed = True
    
    def __init__(self):
        self.status    = False
        self.setting   = {}
        self.localIp   = UtilFunc.getLocalIp()
        self.nsm       = openvpn_manager.OpenvpnManager(self.setting)
        thread.start_new_thread(self._ipWatch, ())
        
    def _ipWatch(self):
        while True:
            localIP = UtilFunc.getLocalIp()
            if localIP != self.localIP and self.nsm.check_state():
                self.nsm.gen_client_conf()
                self.localIp = localIp
            time.sleep(2)
        
    @cherrypy.tools.allow()
    def GET(self, *arg, **params):
        intent = params.get('intent', None)
        if not intent:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        elif intent == 'config':
            conPath = self.nsm.get_client_conf()
            if conPath and os.path.exists(conPath):
                return PostStatic.serve_download(conPath, os.path.basename(conPath))
            else:
                raise cherrypy.HTTPError(464, 'Not Exist')
        elif intent == 'status':
            conPath = self.nsm.get_client_conf()
            lastModify = None
            if conPath and os.path.exists(conPath):
                lastModify = os.path.getmtime(conPath)
            return WebFunc.jsonResult({'status':self.nsm.check_state(),'lastModify':lastModify})
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
                if not self.nsm.check_state():  
                    ret = self.nsm.start()
                    if ret != 0:
                        Log.error('Start OpenVPN Failed! Reason[%s]'%ret)
                        raise cherrypy.HTTPError(462, 'Operation Failed')        
            else:
                if self.nsm.check_state():
                    self.nsm.stop()
                
        cherrypy.response.status = 205
        return 
    
    @cherrypy.tools.allow()
    def DELETE(self, *arg, **params):
        return
    
    