# -*- coding: utf-8 -*-
#author:ZJW

import os
import time
import uuid
import cherrypy
import WebFunc
import ProfileFunc
import SqliteFunc
import UtilFunc
import Log
import PopoConfig

from SearchThread import SearchThread
from SearchStatusThread import SearchStatusThread

class Search:
    
    exposed = True
    def __init__(self):
        self.searchMap     = {} 
        
    def GET(self, *arg, **params):
        sid = WebFunc.checkId(arg, self.searchMap)
        start = int(params.get('offset', 0))
        limit = int(params.get('limit', -1))
        try:
            end = 0
            searchInfo = self.searchMap[sid]['info']
            searchInfo['lastTime'] = int(time.time())
            if limit > 0: end = start + limit
            result = ProfileFunc.getSearchTBWithId(sid, start, end)
            resultLen = len(result)
            if resultLen < limit:
                limit = resultLen
                end = start + limit
            ProfileFunc.delSearchTBWithId(sid, end)
            searchInfo['start'] = end
            Log.info('Get Search Result: start[%d], limit[%d], count[%d]'%(start, limit, len(result)))
            return WebFunc.jsonResult({'files':result, 'finished':searchInfo['finished'], \
                        'folderCount':searchInfo['folderCount'], 'fileCount':searchInfo['fileCount']})
        except Exception, e:
            Log.error("Get Search Result Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
    
    def POST(self, *arg, **params):
        filetype = '.'.join(arg)
        folder = params.get('path', '/')
        keyword = params.get('term', None)
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        
        if not folder or not keyword:
            raise cherrypy.HTTPError(460, 'Bad Parameters')
        
        if filetype and filetype in PopoConfig.filters.keys():
            #sqlStr = 'Select * from filecache where name like "%s" and fileType = "%s"'%('%' + keyword + '%', filetype,)
            datas = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, [], 'name like ? and fileType = ?', ('%' + keyword + '%', filetype,))
            return WebFunc.jsonResult({'files':UtilFunc.formatFilesRet(datas, params)})
        
        recursive = UtilFunc.toBoolean(params.get('recursive', True))
        if UtilFunc.isSlash(folder): path = ProfileFunc.GetBoxDisks()[0]
        else: path = folder
            
        #folder = ProfileFunc.slashFormat(folder)
        if not os.path.exists(folder):
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        if UtilFunc.isLinuxSystem():
            if UtilFunc.isLinuxDiskReadOnly(path):
                raise cherrypy.HTTPError(463, 'Not Permitted')
            if UtilFunc.isLowDiskSpace(path):
                raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
            
        try:   
            searchInfo = {}
            searchInfo['path'] = ''
            searchInfo['folder'] = ''
            searchInfo['folderCount'] = 0
            searchInfo['fileCount'] = 0
            searchInfo['totalSize'] = 0
            searchInfo['finished'] = 0
            searchInfo['start'] = 0
            searchInfo['startTime'] = int(time.time())
            searchInfo['lastTime'] = int(time.time())
            searchInfo['success'] = 0
            Log.debug('Start Search!!!! folder[%s]'%folder)
            uuidStr = None
            while True:
                uuidStr = str(uuid.uuid4())
                if uuidStr not in self.searchMap:
                    ProfileFunc.initSearchDB(uuidStr)
                    searchInfo['id'] = uuidStr
                    thread = SearchThread(searchInfo, keyword, folder, recursive)
                    statusThread = SearchStatusThread(searchInfo,self.searchMap)
                    self.searchMap[uuidStr] = {
                                               'thread':thread,
                                               'statusThread':statusThread,
                                               'info':searchInfo
                                               }
                    thread.start()
                    statusThread.start()
                    break
            cherrypy.response.status = 202
            return WebFunc.jsonResult({"id":uuidStr})
        except Exception, e:
            Log.error("Search Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
    
    def DELETE(self, *arg, **params):
        sid = WebFunc.checkId(arg, self.searchMap)
        try:
            searchInfo = self.searchMap[sid]['info']
            searchInfo['finished'] = 1
    
            del self.searchMap[sid]
            ProfileFunc.delSearchCacheDB(sid)
            Log.debug('Cancel Search!!!!')
 
        except Exception, e:
            Log.error("Cancel Search Failed! Reason[%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed')
        
        cherrypy.response.status = 205
        cherrypy.response.headers['Transfer-Encoding'] = 'chunked'
        return None