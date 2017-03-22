# -*- coding: utf-8 -*-
#author:ZJW

import uuid
import json
import cherrypy
import WebFunc
import ProfileFunc
import UtilFunc
import Log

from BatchThread import BatchThread

class Batch:
    
    exposed = True
    def __init__(self):
        self.operateMap         = {}      
    
    def GET(self, *arg, **params):
        id = WebFunc.checkId(arg, self.operateMap)
        ret = self.operateMap[id]
        ret['progress'] = int(ret['finishedFiles'])*100/int(ret['totalFiles'])
        return WebFunc.jsonResult({'files':ret})
    
    def POST(self, **params):
        action  = params.get('action','')
        files   = params.get('files',[])
        onExist = params.get('onExist','rename')
        if not action or not files: raise cherrypy.HTTPError(460,'Bad Parameters')
        files = UtilFunc.strToList(files)
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        target = params.get('target','')
        if action != 'delete':
            target = params.get('target','')
            if not target:
                Log.error("Operate File Failed, target is None!!!!")
                raise cherrypy.HTTPError(460,'Bad Parameters')
            
            target = ProfileFunc.slashFormat(target)
            if UtilFunc.isLinuxSystem():
                if UtilFunc.isLinuxDiskReadOnly(target):
                    raise cherrypy.HTTPError(463, 'Not Permitted')
                if UtilFunc.isLowDiskSpace(target):
                    raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
                    
        info                  = {}        
        info['totalFiles']    = len(files)
        info['successFiles']  = 0
        info['finishedFiles'] = 0
        info['skipedFiles']   = 0
        info['error']         = []
        info['finished']      = 0
        
        uuidStr = str(uuid.uuid4())
        self.operateMap[uuidStr] = info
        
        thread = BatchThread(info, files, action, target, onExist)
        thread.start()
        
        cherrypy.response.status = 202
        return WebFunc.jsonResult({"id":uuidStr})
    
    def DELETE(self, *arg, **params):
        id = WebFunc.checkId(arg, self.operateMap)
        try:
            b_obj = self.operateMap.pop(id) 
            b_obj['finished'] = 1
            Log.info('Batch[%s] Canceled!!!!'%id)
            cherrypy.response.status = 205
            return
        except Exception, e:
            Log.error("Batch[%s] Failed! Reason[%s]"%(id,e))
            raise cherrypy.HTTPError(462, 'Operation Failed') 
        
        
        