# -*- coding: utf-8 -*-
import os
import types
import cherrypy
import ProfileFunc
import json
import WebFunc
import PubCloudStorage


method_req = {'bind':'BindCloudAccount',\
            'unbind':'UnbindCloudAccount',\
            'account':'GetCloudAccount',
            'token':'GetToken', 
            'status':'QueryJobStatus',
            'record':'GetBackupRecord',
            'all':'GetAllBackupRecords',
            'upload':'BackupToCloud',
            'delete':'DeleteBackupRecords'
            }

error_code = {'471':'BUSY','472':'SESSION_EXPIRED','473':'ALREADY_BIND',\
            '474':'INVALID_PARAMS','475':'AccessTokenError',\
            '476':'CloudUploadError','478':'SERVER_ERROR',\
            '479':'NETWORK_ERROR','480':'JOB_NOT_EXISTS','481':'DATABASE_ERROR',\
            '482':'TIMEOUT','483':'UNSUPPORTED_CLOUD','484':'FILE_NOT_EXISTS',\
            '485':'UNKNOWN_ERROR','486':'UNSUPPORTED_METHODS',\
            '487':'DISK_NOT_MOUNTED','488':'NOT_BIND','489':'AUTH_PENDING','490':'AUTH_DECLINED',\
            '491':'MAX_REQUESTS'}

class Cloud:
    
    exposed = True
    
    def __init__(self):
        self.cloudstorage = PubCloudStorage.PubCloudStorage()
        
    def _requestPubCLoud(self, intent, params):
        cloudargs = params.get('args',{'name':'baidu'})
        try:
            if not isinstance(cloudargs,types.DictType):
                cloudargs = dict(eval(cloudargs.encode('utf-8')))
        except:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if intent in method_req.keys():
            response = self.cloudstorage.handleHttpReq(method_req.get(intent), **cloudargs)
            response = json.loads(response)
            if str(response.get('error_code')) in error_code:
                err = response.get('error_code')
                raise cherrypy.HTTPError(err, error_code.get(err))
            return WebFunc.jsonResult(response)
        raise cherrypy.HTTPError(486,"UNSUPPORTED_METHODS")

    @cherrypy.tools.allow() 
    def GET(self, *arg, **params):
        intent = params.get('intent','')
        if not intent or not intent in ['account','token','status','record','all']:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        return self._requestPubCLoud(intent, params)
        
    @cherrypy.tools.allow() 
    def POST(self, *arg, **params):
        intent = params.get('intent','')
        if not intent or intent != 'upload':
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        return self._requestPubCLoud(intent, params)
    
    @cherrypy.tools.allow() 
    def DELETE(self, *arg, **params):
        intent = 'delete'
        return self._requestPubCLoud(intent, params)
    
    @cherrypy.tools.allow() 
    def PUT(self, *arg, **params):
        intent = params.get('intent','')
        if not intent or not intent in ['bind','unbind']:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        return self._requestPubCLoud(intent, params)
        
    def start(self):
        self.cloudstorage.start()
        
    def stop(self):
        self.cloudstorage.stop()
        

