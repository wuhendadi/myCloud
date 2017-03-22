# -*- coding=utf-8 -*-
#author:LMC

import os
import cherrypy
import time
import WebFunc
import UtilFunc
import Log
import PubCameraCtrl
#import test

error_code = {'460':'Bad Parameters',
              '464':'Not Exist',
              '465':'Not Exist Disk',
              '467':'Not Enough Disk Space',
              '520':'CAMERA_NOT_BIND',
              '521':'CAMERA_PASSWORD_ERROR',
              '523':'CAMERA_HAS_BIND', 
              '524':'CAMERA_IS_ADDING', 
              '525':'CAMERA_ADD_FAILED',
              '526':'CAMERA_IS_UNBINDING',
              '527':'DISK READ ONLY',
              '528':'CAMERA_SERVICE_ERROR',
              '529':'MODIFY_CAMERA_PASSWORD_FAILED',
              '530':'CAMERA_PASSWORD_ERROR'}

class CameraApp:
    
    exposed = True
    
    def __init__(self):
        self.cameraCtrl = PubCameraCtrl.PubCameraCtrl()
        #self.test = test.test()
    
    def _requestPubCamera(self, intent,args, param):
        if intent in self.cameraCtrl.getEventMethods():
            result = self.cameraCtrl.dispatchEvent( intent, args, param)
            if intent == 'stream':
                return result
            if result.has_key('error_code') and str(result.get('error_code')) in error_code:
                err = result.get('error_code')
                raise cherrypy.HTTPError(err, error_code.get(err))
            else:
                return WebFunc.jsonResult(result)
        raise cherrypy.HTTPError(486,"UNSUPPORTED_METHODS")
    
    @cherrypy.tools.allow()
    def GET(self, *arg, **param):
        intent = param.get('intent', None)
        if not intent:
            intent = arg[0]   #Compatibility before
        return self._requestPubCamera( intent, arg[1:],param)
    
    @cherrypy.tools.allow()
    def POST(self, *arg, **param):
        return
    
    @cherrypy.tools.allow()
    def PUT(self, *arg, **param):
        return
    
    @cherrypy.tools.allow()
    def DELETE(self, *arg, **param):
        return

    def start(self):
        self.cameraCtrl.start()
        
#if __name__ == '__main__':
#    camera = CameraApp()
#    
#    ret = camera.GET(intent="hello", str="lmc")
#    print ret
        