# -*- coding = utf-8 -*-
#author:ZJW


import os
import json
import cherrypy
import UtilFunc
import ProfileFunc
import SqliteFunc
import thumbnail
import urllib
import WebFunc
import PostStatic as static

def _formatRet(sqlStr, params):
    datas = SqliteFunc.execSql(sqlStr)
    return UtilFunc.formatMediaRet(datas, params)


class Music:
    
    exposed = True
    
    def GET(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        intent = arg[0]
        if intent == 'all':
            sqlStr = 'select url, name, remarks from fileCache where fileType = "music"'
            return WebFunc.jsonResult({'songs':_formatRet(sqlStr, params)})
        elif intent in ['albums', 'artists', 'genres']:
            key = ''.join(arg[1:])
            if key:
                sqlStr = "select url, name, remarks from fileCache where fileType = 'music'"
                ret = [x for x in _formatRet(sqlStr, {}) if str(x.get(intent[:-1], '')) == key]
                return WebFunc.jsonResult({'songs':UtilFunc.orderAndLimit(ret, params)})
            else:
                ret = []
                tempList = []
                sqlStr = 'select remarks from fileCache where fileType = "music"'
                sqlret = SqliteFunc.execSql(sqlStr)
                for onefile in sqlret:
                    remarks = json.loads(onefile['remarks'])
                    if not remarks: continue
                    if intent == 'albums':
                        if remarks['album'] and not remarks['album'] in tempList:
                            tempList.append(remarks['album'])
                            ret.append({'title':remarks['album'],'artist':remarks['artist'],'year':remarks['year'],
                                        'composer':remarks['composer'],'genre':remarks['genre']})
                    else:
                        if remarks[intent[:-1]] and not remarks[intent[:-1]] in ret:
                            ret.append(remarks[intent[:-1]])
                            
                return WebFunc.jsonResult({intent:UtilFunc.orderAndLimit(ret, params)})
            
        elif intent == 'folders':
            path = UtilFunc.formatPath(arg[1:])
            if not path or not os.path.exists(path):
                raise cherrypy.HTTPError(464, 'Not Exist')
            if not os.path.isdir(path):
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            folders, songs = UtilFunc.walkFolder(path, 'music', params)
            return WebFunc.jsonResult({'folders':folders,'songs':songs})
            
        elif intent == 'stream':
            return UtilFunc.mediaPlay(''.join(arg[1:]))
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def POST(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        intent = arg[0]
        if intent == 'info':
            paths = params.get('paths',None)
            paths = UtilFunc.strToList(paths)
            sqlStr = 'select url, name, remarks from fileCache where fileType = "music"'
            sqlStr += ' and url in (%s)'%','.join(['"' + k + '"' for k in paths])     
            return WebFunc.jsonResult({'songs':_formatRet(sqlStr, params)})
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def PUT(self):
        return
    
class Video:
    
    exposed = True
    
    def GET(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        intent = arg[0]
        if intent == 'all':
            sqlStr = 'select url, name, remarks from fileCache where fileType = "video"'
            return WebFunc.jsonResult({'videos':_formatRet(sqlStr, params)})
            
        elif intent == 'folders':
            path = UtilFunc.formatPath(arg[1:])
            if not path or not os.path.exists(path):
                raise cherrypy.HTTPError(464, 'Not Exist')
            if not os.path.isdir(path):
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            folders, videos = UtilFunc.walkFolder(path, 'video', params)
            return WebFunc.jsonResult({'folders':folders,'videos':videos})
        elif intent == 'thumbnail':
            if len(arg) < 2:
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            tempThumbImage = UtilFunc.getPictureHashPath(''.join(arg[1:]))
            if not tempThumbImage or not os.path.exists(tempThumbImage):
                raise cherrypy.HTTPError(464, 'Not Exist')

            return static.serve_download(tempThumbImage)
        
        elif intent == 'stream':
            return UtilFunc.mediaPlay(''.join(arg[1:]))
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def POST(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        intent = arg[0]
        if intent == 'info':
            paths = params.get('paths',None)
            paths = UtilFunc.strToList(paths)
            sqlStr = 'select url, name, remarks from fileCache where fileType = "video"'
            sqlStr += ' and url in (%s)'%','.join(['"' + k + '"' for k in paths])     
            return WebFunc.jsonResult({'videos':_formatRet(sqlStr, params)})
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def DELETE(self, *arg, **params):
        return
    

# if __name__ == "__main__":
#     s = Music()._getId3TagInfo('D:/ykj.mp3')
#     print s