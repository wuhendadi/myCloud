# -*- coding: utf-8 -*-
#author:ZJW

import os
import time
import cherrypy
import json
import UtilFunc
import WebFunc
import PostStatic
import ProfileFunc
import SqliteFunc
import PopoConfig

from zipstream import ZipStream


def _getvalidity(modifytime, validity):
    if validity == -1: 
        return validity
    return int(validity ) - int((time.time()-int(modifytime)/1000)//86400)

def _formatShare(share):
    return {
            'id'            : share['url'],
            'location'      : share['location'],
            'name'          : share["name"],
            'isFolder'      : share['isFolder'],
            'contentType'   : share['contentType'],
            'extractionCode': share['extractionCode'],
            'validity'      : _getvalidity(share['lastModify'],share['validity']),
            'contentLength' : share['contentLength'],
            'createTime'    : UtilFunc.getUtcTime(share['lastModify']),
            }
    
def _deleteShare(ids):
    ids = UtilFunc.strToList(ids)
    sqlStr = ','.join(["'" + urlId + "'" for urlId in ids])
    #ProfileFunc.execSharesSql("delete from shares where url in (%s)"%sqlStr)
    SqliteFunc.tableRemove(SqliteFunc.TB_SHARES, 'url in (%s)'%sqlStr, )
    conn = ProfileFunc.getMsgChannel()
    msg = {'urlIds':ids}
    conn.send(msg, 0x0043)
    
def _getShare(id, params={}):
    #shares = ProfileFunc.execSharesSql('select * from shares where shareId=?', (id,))
    shares = SqliteFunc.tableSelect(SqliteFunc.TB_SHARES, [], 'shareId=?', (id,))
    if len(shares) == 0:
        return {'errCode':464}
    else :
        share = shares[0]
        extractionCode = str(params.get('extractionCode',''))
        if extractionCode != str(share['extractionCode']):
            return {'errCode':461}
        
        if not os.path.exists(share['location']):
            _deleteShare(id)
            return {'errCode':464}
        
        return _formatShare(share)

class GuestShare:
    
    exposed = True
    
    def _getLocaltion(self, arg):
        if not arg:
            return None
        id = arg[0]
        #share = ProfileFunc.execSharesSql('select location from shares where shareId=?', (id,))
        share = SqliteFunc.tableSelect(SqliteFunc.TB_SHARES, ['location'], 'shareId=?', (id,))
        if len(share) == 0:
            return None
        location = share[0]['location']
        if arg[1:]:
            location = os.path.join(location, '/'.join(arg[1:]))
        return location
    
    def _downloadShare(self, path):
        if not os.path.exists(path):
            return WebFunc.jsonResult({'errCode':464})
        if os.path.isdir(path):
            folderPath = ProfileFunc.slashFormat(path)
            filename = os.path.basename(folderPath)
            filename = filename+'.zip'
            request = cherrypy.serving.request
            filename = UtilFunc.StringUrlEncode(filename)
            
            response = cherrypy.response
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Last-Modified'] = time.time()
            User_Agent = request.headers.get('User-Agent')
            if 'Firefox' in User_Agent: 
                response.headers['Content-Disposition'] = 'attachment;filename*="%s"' %filename
            else:
                response.headers['Content-Disposition'] = 'attachment;filename="%s"' %filename    
                
            zipobj = ZipStream(folderPath)
            return zipobj.__iter__()
        else:
            filename = os.path.basename(path)
            filename = UtilFunc.StringUrlEncode(filename)
            return PostStatic.serve_download(path, filename)
    
    def _fileList(self, folder, params):
        if not os.path.isdir(folder):
            return {'errCode':460}
        files = []
        for filename in os.listdir(folder):
            fileFullPath = os.path.join(folder, filename)
            if UtilFunc.isHiddenFile(fileFullPath) or filename[:5] == ".popo":
                continue
            folder = UtilFunc.getParentPath(fileFullPath)
            fileInfo = UtilFunc.formatFileInfo(fileFullPath)
            if not fileInfo :
                Log.debug("get %s file info failed"%repr(fileFullPath))
                continue
            files.append(fileInfo)
        
        if params.get('order', None):
            files.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, params.get('order')))    
            
        if params.get('limit',-1) >= 0:
            files = files[params.get('offset',0):(params.get('offset',0) + params.get('limit'))]
        else:
            files = files[params.get('offset',0):]
    
        return files
    
    def GET(self, *arg, **params):
        if not arg:
            return WebFunc.jsonResult({'errCode':460})
        if arg[0] == 'download':
            return self._downloadShare(self._getLocaltion(arg[1:]))
        elif arg[0] == 'info':
            return WebFunc.jsonResult(self._fileList(self._getLocaltion(arg[1:]),params))
        else:
            return WebFunc.jsonResult(_getShare(arg[0],params))
        
    GET._cp_config = {'response.stream': True}

class Share:
    
    exposed = True
        
    def _getShares(self):
        #ret = ProfileFunc.execSharesSql('select * from shares')
        ret = SqliteFunc.tableSelect(SqliteFunc.TB_SHARES)
        shares = []
        for share in ret:
            validity = _getvalidity(share['lastModify'],share['validity'])
            if not os.path.exists(share[2]) or (validity <= 0 and str(share['validity']) != '-1'):
                #ProfileFunc.execSharesSql('delete from shares where id = ?',(share[0],))
                SqliteFunc.tableRemove(SqliteFunc.TB_SHARES, 'id = ?', (share[0],))
                continue
            shares.append(_formatShare(share))
            
        return shares
    
    @cherrypy.tools.allow()
    def GET(self, *arg, **params):
        id = ''.join(arg)
        if id:
            return WebFunc.jsonResult(_getShare(id,params))
        else:
            return WebFunc.jsonResult({'shares':self._getShares()})
    
    @cherrypy.tools.allow()
    def POST(self, *arg, **params):
        path = UtilFunc.formatPath(arg)
        if not path: path = params.get('path','')
        isPrivate = UtilFunc.toBoolean(params.get('isPrivate',True))
        validity = int(params.get('validity',-1))
        if not path:
            raise cherrypy.HTTPError(460, 'Bad Parameter')

        if PopoConfig.PlatformInfo == 'Box' and not UtilFunc.getDiskPath(path):
            raise cherrypy.HTTPError(465, 'Not Exist Disk')

        if not os.path.exists(path):
            raise cherrypy.HTTPError(464, 'Not Exist')

        shareId, access = UtilFunc.createShare(path, validity, isPrivate)
        cherrypy.response.status = 201
        
        return WebFunc.jsonResult(_getShare(shareId, {'extractionCode':access}))
    
    @cherrypy.tools.allow()
    def DELETE(self, *arg, **params):
        ids = params.get('shortUrls',None)
        if not ids:
            raise cherrypy.HTTPError(460, 'Bad Parameters')

        _deleteShare(ids)
        cherrypy.response.status = 205
        cherrypy.response.headers['Content-Length'] = '0'
        return
    
    