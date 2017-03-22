# -*- coding: utf-8 -*-
#author: ZJW


import os
import time
import cherrypy
import traceback
import urllib
import UtilFunc
import ProfileFunc
import WebFunc
import VCardParser
import Log


def getContactBackupDir():
    disks = ProfileFunc.GetBoxDisks()
    if not disks:
        return None
    filePath = os.path.join(disks[0], '.popoCloud')
    folder = os.path.join(filePath, 'Contact Backup').replace('\\', '/')
    return folder


class Backup:
    
    exposed = True
 
    def _getContactFolderInfo(self, result, filePath=None):
        if not filePath: return None
        count = 0
        for root, dirs, files in os.walk(filePath, True):
            for file in files:
                if file.startswith('.'): return
                path = os.path.join(root, file)
                try:
                    statInfo = os.stat(path)
                except:
                    Log.error(traceback.format_exc())
                    continue
                
                count += 1
                fileInfo = {}
                fileInfo['name'] = file
                fileInfo['url'] = UtilFunc.toLinuxSlash(path)
                fileInfo['contentType'] = UtilFunc.getFileExt(file)
                fileInfo['contentLength'] = statInfo.st_size
                fileInfo['lastModify'] = int(statInfo.st_mtime * 1000)
                result.append(fileInfo)
                
        return count    
        
    def _getAllContacts(self, arg):
        phoneId = ''.join(arg)
        if phoneId:
            return self._getContactsById(phoneId)
        
        result = []
        self._getContactFolderInfo(result, getContactBackupDir())
        result = sorted(result, key=lambda x : x['lastModify'])
        
        return WebFunc.jsonResult({'contacts':result})
    
    def _getContactsById(self, phoneId):
        path = os.path.join(getContactBackupDir(), phoneId)
        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        result = []
        count = self._getContactFolderInfo(result, path)
        result = sorted(result, key=lambda x : x['lastModify'])
        
        return WebFunc.jsonResult(result)
    
    def _getOneContact(self, arg, params):
        phoneId = ''.join(arg)
        filename = params.get('filename', '')
        if not phoneId or not filename:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        path = os.path.join(getContactBackupDir(), phoneId, filename)
        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        ret = []
        ret = VCardParser.vcf_parser(path)
        return WebFunc.jsonResult({"info":ret})  

    def _getContactCount(self, arg, params):
        phoneId = ''.join(arg)
        if not phoneId:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        path = os.path.join(getContactBackupDir(), phoneId)
        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        result = []
        count = self._getContactFolderInfo(result, path)
        
        if count != 0:
            new_backup = max(result, key=lambda x : x['lastModify'])
            path = new_backup['url']
            count = VCardParser.getCount(path)
        
        return WebFunc.jsonResult({'count':count, 'path':path})
    
    @cherrypy.tools.allow()
    def GET(self, *arg, **params):
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        
        backup_dir = getContactBackupDir()
        if not os.path.exists(backup_dir):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        intent = params.get('intent', 'all')
        if intent == 'count':
            return self._getContactCount(arg, params)
        elif intent == 'contact':
            return self._getOneContact(arg, params)
        elif intent == 'all': 
            return self._getAllContacts(arg) 
    
    @cherrypy.tools.allow()
    def POST(self, *arg, **params):
        cherrypy.response.timeout = 3600 * 24
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        if not ProfileFunc.GetBoxDisks():
            Log.error("ContactFileUpload Failed!")
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
    
        lcHDRS = {key.lower():val for key, val in cherrypy.request.headers.iteritems()}
        tmp_file_path = None
        tmp_file = None
        
        filepath = params.get("filePath", None)          
        if not filepath:  raise cherrypy.HTTPError(460, 'Bad Parameter')
        filepath = unicode(urllib.unquote(filepath.replace("\\","/").strip()).encode('utf-8'))
        contact_dir = getContactBackupDir()
        path = os.path.join(contact_dir, filepath).replace('\\','/')
        
        if UtilFunc.isLinuxDiskReadOnly(path):
            raise cherrypy.HTTPError(463, 'Not Permitted')
        data_length = int(lcHDRS.get("content-length", 0))
        free, capacity = UtilFunc.getRemainSpace(path)
        if free < data_length/1024:
            raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
        try:
            (parentFolder, filename) = os.path.split(path)    
            if not os.path.exists(path): UtilFunc.makeDirs(parentFolder)
            replaceOldFile = UtilFunc.toBoolean(lcHDRS.get('replaceoldfile', True))
            tmp_file_path = os.path.join(parentFolder,".popotmp_"+ str(time.time()*1000)[-8:]).replace('\\','/')
            tmp_file = open(tmp_file_path, "wb")
            tmp_length = 0
            data = cherrypy.request.body.fp
            while True:
                file_data = data.read(8192)
                if not file_data:
                    break
                tmp_length += len(file_data)
                tmp_file.write(file_data)
            tmp_file.close()
            
        except Exception, e:
            Log.error("ContactFileUpload Failed! Reason[%s]"%e)
            if tmp_file: 
                tmp_file.close()
                os.remove(tmp_file_path) 
            raise cherrypy.HTTPError(462, 'Operation Failed')
            
        if tmp_length != data_length:
            os.remove(tmp_file_path) 
            raise cherrypy.HTTPError(468, 'Timeout')
        
        if os.path.exists(path):
            if replaceOldFile: os.remove(path)
            else: path = UtilFunc.setFileName(path)
              
        os.renames(tmp_file_path, path)
        
        result = []
        count = self._getContactFolderInfo(result, parentFolder) 
        if count > 6:
            rm_backup = min(result, key=lambda x : x['lastModify'])
            rm_path = rm_backup['url']
            if os.path.exists(rm_path):
                os.remove(rm_path)
                
        cherrypy.response.status = 201
        return 
        
        
    POST._cp_config = {'response.stream': True}
    
    @cherrypy.tools.allow()
    def DELETE(self, *arg, **params):
        return
    
    