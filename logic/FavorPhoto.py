# -*- coding: utf-8 -*-
import os
import WebFunc
import types
import json
import cherrypy
import ProfileFunc
import UtilFunc
import thumbnail
import PopoConfig
import time
import Log

class Favor:
    exposed = True

    def _getKeyParameter(self, params, key, default=None):
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        
        intent = params.get(key, None)
        if not intent: 
            if default:
                return default
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        return intent
    
    def _setlabel(self, params):
        imagepaths = params.get('imagePaths', [])
        imagefolder = params.get('name','')
        if not imagepaths or not imagefolder:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        imagepaths = UtilFunc.strToList(imagepaths)
        image_num = 0
        image_path=[]

        for imagepath in imagepaths:
            if not os.path.exists(imagepath) or not UtilFunc.isPicturePath(imagepath):
                continue
            hash_value = UtilFunc.getMd5Name(imagepath, PopoConfig.MinWidth,PopoConfig.MinHeight)
            modifyTime = int(time.time())
            size = os.path.getsize(imagepath)

            SqlStr = "replace into fileCache(fileType, url, hash, lastModify,\
            groupTime, contentLength, label) values(?,?,?,?,?,?,?)"
            disk = UtilFunc.getDiskPath(imagepath)
            need_conn = ProfileFunc.getConfDb(disk)
            if ProfileFunc._execSql(need_conn, SqlStr, ('picture', imagepath, hash_value, modifyTime, 'label', size, imagefolder,)):
                image_num+=1
                image_path.append(imagepath)
        return WebFunc.jsonResult({"total":image_num,"imagePaths":image_path})


    def _dellabel(self, params):
        names = params.get('names', None)
        names= UtilFunc.strToList(names)
        SqlStr = "delete from fileCache where label=?"
        for name in names:
            ProfileFunc.execAllScanFolderSql(SqlStr, (name, ))
        cherrypy.response.status = 205
        return 
        
    def _delalllabel(self):
        SqlStr = "delete from fileCache"
        ProfileFunc.execAllScanFolderSql(SqlStr)
        cherrypy.response.status = 205
        return 
    
    def _delfromlabel(self, params):
        imagepaths = params.get('imagePaths', [])
        imagefolder = params.get('name','')
        if not imagepaths or not imagefolder:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        imagepaths = UtilFunc.strToList(imagepaths)
        del_num = 0
        del_path = []

        for imagepath in imagepaths:
            if not os.path.exists(imagepath) or not UtilFunc.isPicturePath(imagepath):
                continue
            del_num +=1
            del_path.append(imagepath)
            SqlStr = "delete from fileCache where url=? and label=?"
            ProfileFunc.execAllScanFolderSql(SqlStr, (imagepath, imagefolder, ))
        return WebFunc.jsonResult({"total":del_num, "removePaths":del_path})
    
    @cherrypy.tools.allow() 
    def GET(self, *arg, **params):
        return
    
    @cherrypy.tools.allow() 
    def POST(self, *arg, **params):
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        intent = params.get('intent','set')
        if intent == 'set':
            return self._setlabel(params)
        return
    
    @cherrypy.tools.allow() 
    def PUT(self, *arg, **params):
        return 

    @cherrypy.tools.allow() 
    def DELETE(self, *arg, **params):
        intent = self._getKeyParameter(params,'intent','label')
        if intent == 'label':
            return self._dellabel(params)
        elif intent == 'images':
            return self._delfromlabel(params)
        elif intent == 'all':
            return self._delalllabel()

        return
