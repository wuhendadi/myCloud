# -*- coding: utf-8 -*-
#author:ZJW

import os
import json
import cherrypy
import tempfile
import zipfile
import UtilFunc
import WebFunc
import thumbnail
import ProfileFunc
import SqliteFunc
import PopoConfig
import PostStatic as static
import Log


class Photos:
    
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
    
    def _getFolderPhotos(self):
        return
    
    def _getImageGroup(self, groupType, params):
        orderBy = params.get('order', None)
        limit = int(params.get('limit',1))
        groupDict = {'date':'groupTime','folders':'folders','tags':'tag'}
        if not groupType in groupDict.keys():
            raise cherrypy.HTTPError(460,'Bad Parameter')
        
        group_name = groupDict[groupType]
        scan_list_p = []
        if group_name == 'folders' and not ProfileFunc.getAllMediaFolders():
            raise cherrypy.HTTPError(464, 'Not Exist')
        
        if groupType == 'tags':
            #sqlStr = 'select tag, count(*) from (select * from fileCache where fileType="picture") group by tag'
            #groups = ProfileFunc.execAllScanFolderSql(sqlStr)
            sqlStr = 'select tag, count(*) from (select * from tags where fileType="picture") group by tag'
            groups = SqliteFunc.execSql(sqlStr)
            return WebFunc.jsonResult({'tags':[{'name':file['tag'],'total':file['count(*)']} for file in groups]})
        
        elif groupType == 'folders':
            SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, "folder is ''")
            scan_list= ProfileFunc.getAllSetFolders()
            for path_ele in set(scan_list):
                if not UtilFunc.is_sub_folder(path_ele, scan_list):
                    scan_list_p.append(path_ele)
            ret_list_info = []
            for ret_path in scan_list_p:
                if os.path.exists(ret_path):
                    ret_list_info.append(ProfileFunc.dir_info(ret_path))
                else:
                    SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, 'url=?', (ret_path,))
                    
            return WebFunc.jsonResult({'groupType'  : group_name,
                                       'folders'    : UtilFunc.formatPhotoRet(ret_list_info, params)})
        else:
            start = params.get('start', '1970-01')
            end = params.get('end', '9999-12')
            
            baseStr = 'select * from fileCache where fileType="picture" and groupTime >= "%s" and groupTime <="%s"'%(start,end)
            sqlStr = 'select groupTime, count(*) from (%s) group by groupTime order by lastModify asc'%baseStr
            #groups = SqliteFunc.execSql(sqlStr)
            groups = SqliteFunc.execSql(sqlStr)
            if not groups:
                for disk in ProfileFunc.GetBoxDisks():
                    if ProfileFunc.getMainServer().diskState.has_key(disk) and \
                    ProfileFunc.getMainServer().diskState[disk] == 2:
                        raise cherrypy.HTTPError(463, 'Not Permitted')
                    
                    if UtilFunc.isLowDiskSpace(disk):
                        raise cherrypy.HTTPError(467, 'Not Enough Disk Space')
    
            ret, ret_count, tmp_ret_dict = [], 0, {}
            for fileInfo in groups:
                if not tmp_ret_dict.has_key(fileInfo[group_name]):
                    tmp_ret_dict[fileInfo[group_name]] = ret_count
                else:
                    ret[tmp_ret_dict[fileInfo[group_name]]]['total'] += fileInfo['count(*)']
                    continue
                ret_count += 1
                dbList = SqliteFunc.execFileCacheTags(' and a.%s = "%s"'%(group_name, fileInfo[group_name]))
                photos = UtilFunc.formatPhotoRet(dbList, params)
                if not photos: continue
                ret.append({'name'  : fileInfo[group_name],
                            'total' : fileInfo['count(*)'],
                            'photos': photos})
            if orderBy:
                cmpInfo = UtilFunc.httpArgToCmpInfo(orderBy)
                if len(cmpInfo) > 0 :
                    ret.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, cmpInfo))
                    
            return WebFunc.jsonResult({groupType:ret})
    
    def _getGroupFiles(self, groupType, groupValue, params):
        if groupType == 'tags':
            files = SqliteFunc.execFileCacheTags(' and a.tag = "%s"'%groupValue[0], False, params = params)
        elif groupType == 'folders':
            folder = UtilFunc.formatPath(groupValue)
            if not os.path.isdir(folder):
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            
            folders, photos = UtilFunc.walkFolder(folder, 'picture', params)
            return WebFunc.jsonResult({'folders':folders,'photos':photos})
            
        elif groupType == 'date':
            files = SqliteFunc.execFileCacheTags(' and a.groupTime = "%s"'%groupValue[0], params = params)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
        return WebFunc.jsonResult({'photos':UtilFunc.formatPhotoRet(files, {})})
    
    def _getThumbImage(self, tempThumbImage, ext):        
        if not tempThumbImage or not os.path.exists(tempThumbImage):
            raise cherrypy.HTTPError(464, 'Not Exist')

        return static.serve_file(tempThumbImage,thumbnail.getImageTypes()[ext])
        
    def _getThumbImageZip(self, photos):
        photos = UtilFunc.strToList(photos)
        tempZipFile = tempfile.mktemp(suffix='.zip')
        zf = zipfile.ZipFile(tempZipFile, 'w', zipfile.zlib.DEFLATED)
        path2ThumbMap = ""
        for hash_name in photos:
            tempThumbImage = None
            if hash_name == "0": continue
            tempThumbImage = UtilFunc.getPictureHashPath(hash_name)
            if not tempThumbImage: continue
            name = os.path.basename(tempThumbImage)
            path2ThumbMap += '"' + name + '":"' + hash_name + '"' + ","
            zf.write(tempThumbImage, name)
        if path2ThumbMap == "":
            path2ThumbMap = "{}"
        else:
            path2ThumbMap = "{" + path2ThumbMap[:-1] + "}"
            
        zf.writestr('Path2ThumbMap.json', path2ThumbMap)
        zf.close()
        ret = static.serve_download(tempZipFile)

        #os.close(fd)
        if UtilFunc.isLinuxSystem():
            os.remove(tempZipFile)

        return ret
    
    def _getAutoUploads(self, phoneId):
        if not phoneId:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        Update_path = ProfileFunc.getAutoUploadPath()
        if not Update_path: raise cherrypy.HTTPError(464, 'Not Exist')
        Update_path = os.path.join(Update_path, phoneId).replace("\\","/")
        #if not os.path.exists(Update_path): raise cherrypy.HTTPError(464, 'Not Exist')    
        if not os.path.exists(Update_path): os.mkdir(Update_path)
        if UtilFunc.isLinuxSystem():
            if UtilFunc.isLinuxDiskReadOnly(Update_path):
                raise cherrypy.HTTPError(463, 'Not Permitted')  
        try:
            result = [filename for filename in os.listdir(Update_path)] 
        except Exception, e:
            Log.error("CheckAutoUploadImage Failed! reason: [%s]"%e)
            raise cherrypy.HTTPError(462, 'Operation Failed') 
            
        return WebFunc.jsonResult({'data':result, 'path':Update_path})
    
    def _searchImages(self, params):
        start = int(params.get('offset', 0))
        limit = int(params.get('limit', -1))
        name = params.get('key', None)
        if not name or start < 0:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        files = SqliteFunc.execFileCacheTags(' and a.name like '%" + name + "%'')
        if limit == -1:
            file_info = files[start:]
            finished = 1
        elif int(start) >= 0 and int(start+limit)<len(files):
            file_info= files[start:(start+limit)]
            finished = 0
        elif int(start) >=0 and (start+limit) >= len(files):
            file_info = files[start:len(files)]
            finished = 1
        ret = UtilFunc.formatPhotoRet(file_info, {'order':params.get('order',None)})

        return WebFunc.jsonResult({'photos':ret,'finished':finished})

    def GET(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if arg[0] in ['date','folders','tags']:
            if len(arg) > 1:
                return self._getGroupFiles(arg[0],arg[1:], params)
            else:
                return self._getImageGroup(arg[0], params)
        elif arg[0] == 'thumbnail':
            if len(arg) < 2:
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            return self._getThumbImage(UtilFunc.getPictureHashPath(''.join(arg[1:])), '.jpg')
        elif arg[0] == 'create':
            if len(arg) < 2:
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            path = UtilFunc.formatPath(arg[1:])
            size = int(params.get('size', 170))
            (tempThumbImage,ext) = thumbnail.getThumbNailImage(path,size)
            return self._getThumbImage(tempThumbImage, ext)
            
        elif arg[0] == 'all':
            ret = UtilFunc.formatPhotoRet(SqliteFunc.execFileCacheTags(), params)
            return WebFunc.jsonResult({'photos': ret})
        else:
            return self._getAutoUploads(arg[0])
    
    def POST(self, *arg, **params):
        if not arg:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        if arg[0] == 'search':
            return self._searchImages(params)
        elif arg[0] == 'thumbnail':
            photos = params.get('thumbnailIds',[])
            if not photos:
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            
            return self._getThumbImageZip(photos)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    def PUT(self, *arg, **params):
        if arg and arg[0] == 'tags':
            path = UtilFunc.formatPath(arg[1:])
            tags = params.get('tags',[])
            if path:
                if not os.path.exists(path): raise cherrypy.HTTPError(464, 'Not Exists')
                ProfileFunc.optionTags(path, tags)
            else:
                photos = params.get('photos',[])
                tags = params.get('tags',[])
                action = params.get('action','add')
                for photo in photos:
                    if os.path.exists(photo):
                        ProfileFunc.optionTags(photo,tags,action)
            
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        cherrypy.response.status = 205
        return 
            
    def DELETE(self, *arg, **params):
        if arg:
            if arg[0] == 'tags':
                tags = params.get('tags',[])
                filetype = params.get('fileType', 'picture')
                if not tags: raise cherrypy.HTTPError(460, 'Bad Parameter')
                tags = json.loads(tags)
                for tag in tags: 
                    #ProfileFunc.removeLabels(tag)
                    SqliteFunc.tableRemove(SqliteFunc.TB_TAGS, 'tag = ? and fileType= ?', (tag,filetype,))

            elif arg[0] == 'date':
                dates = params.get('dates',[])
                if not dates:raise cherrypy.HTTPError(460, 'Bad Parameter')
                dates = json.loads(dates) 
                for date in dates:
                    photos = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, ['url'], 'groupTime = "%s"'%date)
                    for photo in photos:
                        if os.path.exists(photo['url']): os.remove(photo['url'])
                    SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, 'groupTime = "%s"'%date)
        else:
            raise cherrypy.HTTPError(460, 'Bad Parameter')
        
        cherrypy.response.status = 205
        return


