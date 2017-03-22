# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import urllib
import uuid
import shutil
import traceback
import cherrypy
import UtilFunc
import ProfileFunc
import SqliteFunc
import WebFunc
import PopoConfig
import Log

from TraversalFolderThread import TraversalFolderThread
from TraversalFolderThreadStatus import TraversalFolderThreadStatus

CRLF    = '\r\n'

def _createFolder(path, params):
    if os.path.exists(path):
        raise cherrypy.HTTPError(469, 'Already Exist')
    if params.get('nested', None): 
        os.makedirs(path)
        cherrypy.response.status = 201
        return 
    else:
        try:
            os.mkdir(path)
        except:
            raise cherrypy.HTTPError(463, 'Not Permitted')

    
def _createFile(path, onExist, params):
    (folder, filename) = os.path.split(path)
    if not os.path.exists(folder): raise cherrypy.HTTPError(463, 'Not Permitted')
    if not onExist: onExist = 'error'
    size = params.get('size',None)
    if not size: raise cherrypy.HTTPError(460, 'Bad Parameter')
    free, capacity = UtilFunc.getRemainSpace(path)
    if free < int(size)/1024:
        raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
    
    sparseFile = UtilFunc.toBoolean(params.get('sparseFile', False))
    if os.path.exists(path):
        if onExist == 'error':
            raise cherrypy.HTTPError(469, 'Already Exist')
        elif onExist == 'overwrite':
            os.remove(path)
            
    file = open(path,'w')
    if sparseFile:
        file.truncate(int(size))
    else:
        file.seek(int(size))
        file.write(' ')
    file.close()
    
    cherrypy.response.status = 201
    return

def createFile(path, onExist, params):
    (folder, filename) = os.path.split(path)
    if not os.path.exists(folder): raise cherrypy.HTTPError(463, 'Not Permitted')
    if not onExist: onExist = 'error'
    size = params.get('size',None)
    if not size: raise cherrypy.HTTPError(460, 'Bad Parameter')
    free, capacity = UtilFunc.getRemainSpace(path)
    if free < int(size)/1024:
        raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
    
    sparseFile = UtilFunc.toBoolean(params.get('sparseFile', False))
    if os.path.exists(path):
        if onExist == 'error':
            raise cherrypy.HTTPError(469, 'Already Exist')
        elif onExist == 'overwrite':
            os.remove(path)
            
    file = open(path,'w')
    if sparseFile:
        file.truncate(int(size))
    else:
        file.seek(int(size))
        file.write(' ')
    file.close()

class Files:
    
    exposed = True
    def __init__(self,parent = None):
        self.parent       = parent
        self.traversalMap = {}
    
    def _updateFile(self, path, params):
        name = params.get('name','')
        lastModify = params.get('lastModify','')
        if name: 
            newpath = os.path.join(os.path.dirname(path), name)
            if os.path.exists(newpath):
                raise cherrypy.HTTPError(469, 'Already Exist')
            os.rename(path, newpath)
            sqlStr = 'update fileCache set url = ?, name = ? where url = ?'
            #ProfileFunc.execSubLibrarySqlbyPath(path, sqlStr, (newpath, name, path,))
            SqliteFunc.execSql(sqlStr, (newpath, name, path,))
            path = newpath
            
        if lastModify:
            UtilFunc.setFileTime(path, lastModify)
            sqlStr = 'update fileCache set lastModify =? where url = ?'
            #ProfileFunc.execSubLibrarySqlbyPath(path, sqlStr, (lastModify, path,))
            SqliteFunc.execSql(sqlStr, (lastModify, path,))
        
        cherrypy.response.status = 205
    
    def _upload(self, path, data_length):
        cherrypy.response.timeout = 3600 * 24
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        path = unicode(urllib.unquote(path.replace("\\","/").strip()).encode('utf-8')) 
        (parentFolder, filename) = os.path.split(path)
        try:
            tmp_file_path = os.path.join(parentFolder,".popotmp_"+ str(time.time()*1000)[-8:])
            tmp_file = open(tmp_file_path, "wb")
            tmp_length = 0
            data = cherrypy.request.body.fp
            while True:
                file_data = data.read(8192)
                if not file_data: break
                tmp_length += len(file_data)     
                tmp_file.write(file_data)
                WebFunc.refreshToken()
            tmp_file.close()
            
            if tmp_length != data_length:
                os.remove(tmp_file_path)
                return None
            return tmp_file_path
        except Exception, e:
            Log.exception('Files Upload Failed! Reason[%s]'%e)
            if tmp_file: 
                tmp_file.close()
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)  
            return None
        
    def _formatPath(self, arg, params, Exist=True):
        if not arg: 
            path = params.get('path',None)
        else: 
            path = UtilFunc.formatPath(arg) 
        if not path:
            raise cherrypy.HTTPError(460,'Bad Parameter')
        path = unicode(path.strip('\''))
        if not os.path.exists(path) and Exist:
            raise cherrypy.HTTPError(464, 'Not Exist')
        if UtilFunc.isLinuxDiskReadOnly(path):
            raise cherrypy.HTTPError(463, 'Not Permitted')
        
        return path
    
    def _getTraversalResult(self, arg, params):
        id = WebFunc.checkId(arg, self.traversalMap)
        start = int(params.get('offset', 0))
        limit = int(params.get('limit', -1))

        try:
            ret = []
            end = 0
            traversalInfo = self.traversalMap[id]['info']
            traversalInfo['lastTime'] = int(time.time())
            if limit > 0: end = start + limit
            result = ProfileFunc.getTraversalTBWithId(id, start, end)
            resultLen = len(result)
            if resultLen < limit:
                limit = resultLen
                end = start + limit
            ProfileFunc.delTraversalTBWithId(id, end)
            traversalInfo['start'] = end
            Log.info('Get TraversalFolder Result:start[%d], limit[%d], count[%d]'%(start, limit, len(result)))
            return WebFunc.jsonResult({'files':result, 'finish':traversalInfo['finished'], \
                        'fileCount':traversalInfo['fileCount'], 'folderCount':traversalInfo['folderCount']})
        except Exception, e:
            Log.error("Get Traversal Folder Result Failed! Reason[%s]"%e)
            return cherrypy.HTTPError(462, 'Operation Failed')
             
    def _traversalFolder(self, path):
        if not path:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
                
        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        if UtilFunc.isLinuxSystem():
            if UtilFunc.isLinuxDiskReadOnly(path):
                raise cherrypy.HTTPError(463, 'Not Permitted')
            if UtilFunc.isLowDiskSpace(path):
                raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
        
        try: 
            traversalInfo                   = {}
            traversalInfo['path']           = ''
            traversalInfo['fileCount']      = 0
            traversalInfo['folderCount']    = 0
            traversalInfo['totalSize']      = 0
            traversalInfo['finished']       = 0
            traversalInfo['start']          = 0
            traversalInfo['folder']         = ''
            traversalInfo['startTime']      = int(time.time())
            traversalInfo['lastTime']       = int(time.time())
            traversalInfo['success']        = 0
            Log.info('Start Traversal Folder!!!!')
            uuidStr = None
            while True:
                uuidStr = str(uuid.uuid4())
                if uuidStr not in self.traversalMap:
                    ProfileFunc.initTraversalDB(uuidStr)
                    traversalInfo['id'] = uuidStr
                    thread = TraversalFolderThread(traversalInfo, path)
                    threadStatus = TraversalFolderThreadStatus(traversalInfo,self.traversalMap)
                    self.traversalMap[uuidStr] = {
                                               'thread':thread,
                                               'threadStatus':threadStatus,
                                               'info':traversalInfo
                                               }
                    thread.start()
                    threadStatus.start()
                    break
            cherrypy.response.status = 202
            return WebFunc.jsonResult({"id":uuidStr})
        except Exception, e:
            Log.error("Traversal Folder Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
    def _cancelTraversalFolder(self, arg):
        sid = WebFunc.checkId(arg, self.traversalMap)
        try:
            traversalMapEntry           = self.traversalMap[sid]
            traversalInfo               = traversalMapEntry['info']
            traversalInfo['finished']   = 1
    
            del self.traversalMap[sid]
            ProfileFunc.delTraversalCacheDB(sid)
            Log.info('Cancel Traversal Folder!!!!')
        except Exception, e:
            Log.exception("Cancel Traversal Folder Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
        cherrypy.response.status = 205
        return
    
    def _getLibraryGroupByType(self, params):
        typeName = params.get('fileType', None)
        orderBy = params.get('orderBy', None)
        if not typeName or not typeName in (PopoConfig.filters.keys() + ['other']):
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        datas = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, [], 'fileType= ?', (typeName,), params)

        return WebFunc.jsonResult({'fileType':typeName, 'datas':UtilFunc.formatFilesRet(datas, {})})
    
    def _decodeChunked(self, content): 
        content = content.lstrip('\r') 
        content = content.lstrip('\n') 
        temp = content.find('\r\n') 
        strtemp = content[0:temp] 
        readbytes = int(strtemp, 16) 
        newcont = '' 
        start = 2 
        offset = temp + 2 
        newcont = ''
        while(readbytes > 0): 
            newcont += content[offset:readbytes + offset] 
            offset += readbytes 
            endtemp = content.find('\r\n', offset + 2) 
            if(endtemp > -1): 
                strtemp = content[offset + 2:endtemp] 
                readbytes = int(strtemp, 16) 
                if(readbytes == 0): 
                    break 
                else: 
                    offset = endtemp + 2 
                    content = newcont 
                    return content
        
    @cherrypy.tools.allow()
    def GET(self, *arg, **params):
        extInfo = UtilFunc.getOptParamsInfo(params)
        intent = params.get('intent', None)
        if intent == 'traversal':
            return self._getTraversalResult(arg, params)
        elif intent == 'typeFile':
            return self._getLibraryGroupByType(params)
        elif arg and arg[0] == 'stream':
            return UtilFunc.mediaPlay(''.join(arg[1:]))
        path = self._formatPath(arg, params)
        if intent == 'props':
            return WebFunc.jsonResult(UtilFunc.getFileInfo(path, extInfo, True))
        elif intent == 'folderZip':
            return WebFunc.DownloadFolderZip(path)
        if os.path.isdir(path):
            files = UtilFunc.getFileList(path, extInfo)
        else:
            headers = {key.lower():val for key, val in cherrypy.request.headers.iteritems()}
            lastEtag = headers.get('if-none-match',None)
            etag = UtilFunc.getFileEtag(path)
            if lastEtag:
                if lastEtag == etag:
                    cherrypy.response.status = 304
                    return
            matchEtag = headers.get('if-match',None)
            if matchEtag:
                if matchEtag != etag:
                    raise cherrypy.HTTPError(412)
            return WebFunc.DownloadFile(path)
        
        return WebFunc.jsonResult({'total':len(files),'files':files,'offset':extInfo['offset'],'limit':extInfo['limit']})
        
    GET._cp_config = {'response.stream': True}
    
    @cherrypy.tools.allow() 
    def POST(self, *arg, **params):
        #path = self._formatPath(arg, params, False)
        path = UtilFunc.getDefaultPath(self._formatPath(arg, params, False))
        onExist, intent = params.get('onExist', None), params.get('intent', None)
            
        if intent == 'newFolder': return _createFolder(path, params)
        elif intent == 'newFile': return _createFile(path, onExist, params)
        elif intent == 'traversal': return self._traversalFolder(path)
        if not intent and os.path.isdir(path):
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if os.path.exists(path) and onExist == 'error':
            raise cherrypy.HTTPError(469, 'Already Exist')
        parentfolder = os.path.dirname(path)
        lcHDRS = {key.lower():val for key, val in cherrypy.request.headers.iteritems()}
        size = int(lcHDRS.get('content-length'))
        free, capacity = UtilFunc.getRemainSpace(path)
        if free < size/1024:
             raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
        try:
            if not os.path.exists(parentfolder): os.makedirs(parentfolder)    
            tmp_file = self._upload(path, size)
            if not tmp_file: raise cherrypy.HTTPError(463, 'Not Permitted')
            if not onExist or onExist == 'overwrite': 
                if os.path.exists(path): os.remove(path)
            elif onExist == 'rename': path = UtilFunc.setFileName(path)
            os.renames(tmp_file, path)
            ProfileFunc.addFileCache(path)
            UtilFunc.setFileTime(path, params.get('lastModify',None))
#             image_md5 = params.get('isAutoUpload',False)
#             if image_md5:
#                 ProfileFunc.execImageCacheSql(parentfolder, "insert into imageCache(name) values(?)", (image_md5,))
        except Exception, e:
            Log.exception('Upload File Failed! Reason[%s]'%e)
            raise cherrypy.HTTPError(463, 'Not Permitted')
        
        cherrypy.response.status = 201
        return
        
    POST._cp_config = {'response.stream': True}
    
    @cherrypy.tools.allow() 
    def DELETE(self, *arg, **params):
        intent = params.get('intent', None)
        if intent == 'traversal':
            return self._cancelTraversalFolder(arg)
        path = self._formatPath(arg, params)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                ProfileFunc.delFileCache(path)
#                 removeSql = "delete from fileCache where url='%s'"%path
#                 ProfileFunc.execSubLibrarySqlbyPath(path, removeSql)
        except Exception,e:
            Log.exception('Files DELETE Excepted! Reason[%s]'%e)
            raise cherrypy.HTTPError(463, 'Not Permitted')
        
        cherrypy.response.status = 205
        return 
    
    @cherrypy.tools.allow() 
    def PUT(self, *arg, **params):
        path = self._formatPath(arg, params)
        intent = params.get('intent', None)
        if intent:
            if intent.lower() != 'props':
                raise cherrypy.HTTPError(460,'Bad Parameter')
            else:
                return self._updateFile(path, params)
        else:
            if not path or not os.path.isfile(path):
                raise cherrypy.HTTPError(460,'Bad Parameter')
            tempFile = open(path, 'wb')
            headers = {key.lower():val for key, val in cherrypy.request.headers.iteritems()}
            contentRange = headers.get('content-range',None)
            if not contentRange: 
                raise cherrypy.HTTPError(460,'Bad Parameter')
            ranges = re.findall(r'(\d+)', contentRange)
            if len(ranges) <= 1: 
                start, end, length = 0, int(ranges[0]), int(ranges[0])
            else:
                start, end, length = int(ranges[0]), int(ranges[1]), int(ranges[2])
            if end > length: 
                raise cherrypy.HTTPError(416, 'Requested Range Not Satisfiable')
            tempFile.seek(start)
            data = cherrypy.request.body.fp
            content_length = headers.get('content-length', None)
            if content_length:
                content_length = int(content_length)
                curr_length, buf = 0, 8192
                while content_length - curr_length > 0:
                    if content_length - curr_length < 8192:
                        buf = content_length - curr_length
                    file_data = data.read(buf)
                    if not file_data: break    
                    tempFile.write(file_data)
                    curr_length += len(file_data)         
            else:
                chunk_data = self._decodeChunked(data.read())
                tempFile.write(chunk_data)
                
            tempFile.close()
            cherrypy.response.status = 204
            return 
    
    @cherrypy.tools.allow() 
    def PATCH(self, **params):
        return
    
    @cherrypy.tools.allow() 
    def OPTIONS(self, **params):
        return
