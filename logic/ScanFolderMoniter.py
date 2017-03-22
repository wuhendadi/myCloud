# -*- coding=utf-8 -*-
#author:ZJW

import os
import re
import thread
import time
import types
import threading
import cherrypy
import Command
import Error
import json
import ProfileFunc
import SqliteFunc
import UtilFunc
import PopoConfig
import thumbnail
import Log

from PopoConfig import filters

STATUS_IDLE = 0
STATUS_WORK = 1
STATUS_STOP = 2

class scanFolderCtrl(threading.Thread):
    
    def __init__(self, del_set, scan_set):
        threading.Thread.__init__(self)
        self.scan_set = scan_set
        self.del_set = del_set
        self.stop_flag = False
        
    def _listSubFolder(self, folder):
        folder = json.loads(folder)
        path, type = folder['folder'].encode('utf8'), folder['type']
        for p_dir, _, _ in os.walk(path):
            if not '.popoCloud' in p_dir and not p_dir.split('/')[-1].startswith('.'):
                try:
                    yield json.dumps({'folder':p_dir.encode('utf8'),'type':type})
                except:
                    yield json.dumps({'folder':p_dir.decode('gbk'),'type':type})
        
    def _remove(self, all_del_set, flag=False):
        for fullpath in all_del_set:
            del_scan_path = UtilFunc.getSiteRoot(fullpath)
            if flag:
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)),\
                        "delete from mediafolder where url=?", (del_scan_path, ))
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)),\
                        "delete from selectfolder where url=?", (del_scan_path, ))
                del_scan_path_like = del_scan_path+'/%'
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)),\
                        "delete from mediafolder where url like ?", (del_scan_path_like, ))
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)),\
                        "delete from selectfolder where url like ?", (del_scan_path_like, ))
                SqliteFunc.execSql("delete from fileCache where folder like ?", (fullpath, ))
            if not self.stop_flag:
                ProfileFunc.removeFromLibrary(fullpath)
            else:
                break

    def _add(self, folders, flag=False, type = 'all'):
        for subfolder in folders:
            subfolderdict = json.loads(subfolder)
            fullpath,type = subfolderdict['folder'], subfolderdict['type']
            need_scan_path = UtilFunc.getSiteRoot(fullpath)
            if flag:
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)),\
                        "replace into selectfolder(url) values(?)", (need_scan_path, ))

            if not self.stop_flag:
                ProfileFunc._execSql(ProfileFunc.getConfDb(UtilFunc.getDiskPath(fullpath)), 'replace into \
                mediafolder(url, type) values(?, ?)', (need_scan_path, type,))
                ProfileFunc.addToLibrary(fullpath, flag, type)
            else:
                break
            
    def run(self):
        self._remove(self.del_set, True)
        self._add(self.scan_set, True)
        all_scan_set = set()
        for scan_path in self.scan_set:
            all_scan_set = all_scan_set|set(self._listSubFolder(scan_path))
        self._add(all_scan_set)
    
    def stop(self, stop_flag=False):
        self.stop_flag = stop_flag


class ScanFolderMoniter:

    def __init__(self, parent):
        self.status          = STATUS_IDLE
        self.mainService     = parent
        self.folders         = {}
        
    def _initMediaFolder(self, key, folders, status, recursive):
        if not self.folders.has_key(key):
            self.folders[key] = {'folders':folders, 'status':status, 'recursive':recursive}
        
    def _scanFolder(self, scanPath, diskPath, recursive= False, scanType = 'all'):
        folder = unicode(scanPath.replace('\\','/'))
        if not os.path.exists(folder): return
        for sub_file in os.listdir(folder):
            if not recursive and not {'folder':scanPath, 'type':scanType} in self.folders[diskPath]['folders']: return
            if sub_file == '.popoCloud' or sub_file == '.cameraApp': continue
             
            path = unicode(os.path.join(folder, sub_file))
            if not os.path.exists(path) or sub_file[-4:] == ".lnk" or UtilFunc.isHiddenFile(path):
                continue
             
            if UtilFunc.isShorcut(path):
                path = UtilFunc.getShortcutRealPath(path)
                if path and os.path.isdir(path):
                    self.mainService.folderMoniter.addDisk(path)
                 
            if os.path.isdir(path):
                if recursive:
                    self._scanFolder(path, diskPath, recursive)
                continue
            ProfileFunc.addFileCache(path, scanType)
            
#     def _scanFolder(self, scanPath, diskPath, recursive= False, scanType = 'all'):
#         folder = unicode(scanPath.replace('\\','/'))
#         if not os.path.exists(folder): return
#         for dir, subdirs, files in os.walk(folder):
#             if UtilFunc.isHiddenFile(dir): continue
#             for file in files:
#                 path = os.path.join(dir,file) 
#                 if not os.path.exists(path) or file[-4:] == ".lnk" or UtilFunc.isHiddenFile(path):
#                     continue
#                 
#                 ProfileFunc.addFileCache(path)
            
    def _isAllDiskScaned(self):
        for k in self.folders.keys():
            if self.folders[k]['status'] == STATUS_WORK:
                return False
        return True
    
    def _delNotExistImageThumb(self, disk):
        #files = ProfileFunc.execSubLibrarySqlbyPath(disk, 'select remarks from fileCache where fileType = "picture" or fileType = "video"', None) 
        files = SqliteFunc.execSql('select remarks from fileCache where fileType = ? or fileType = ?', ('picture','video',))
        hash_list = []
        if not files: return
        for fileInfo in files:
            remarks = json.loads(fileInfo['remarks'])
            hash_list.append(remarks['thumbnail-small'])
            hash_list.append(remarks['thumbnail-large'])

        thumbImage_path = os.path.join(UtilFunc.getDiskPath(disk, True), ".popoCloud/ThumbImage").replace("\\","/")
        try:
            for folder in os.listdir(thumbImage_path):
                folder_path = os.path.join(thumbImage_path, folder).replace("\\","/")
                if not os.path.isdir(folder_path):
                    continue
                for thunmbNail in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, thunmbNail).replace("\\", "/")
                    if not thunmbNail in hash_list:
                        os.remove(file_path)
                if not os.listdir(folder_path):
                    os.rmdir(folder_path)
        except Exception, e:
            Log.error("DelNotExistImageThumb Failed! Reason[%s]"%e)
        
        del hash_list
        
    def _buildScanFolder(self, diskPath, recursive=True):
        if UtilFunc.isLinuxDiskReadOnly(diskPath):
            Log.warning("Warning! Disk[%s] Read-Only!"%diskPath)
            self.mainService.diskState[diskPath] = 2
            return
        Command.ledFlash(1)
        Log.info('Start ScanDisk[%s], Please Wait!'%diskPath)
        self.mainService.diskState[diskPath] = 3
        for item in self.folders[diskPath]['folders']:
            try:
                scanPath, scanType = item['folder'].encode('utf8'), item['type']
                start_time = UtilFunc.Now()           
                if UtilFunc.isLinuxSystem():
                    self.mainService.folderMoniter.addDisk(diskPath)
                self._scanFolder(scanPath, diskPath, recursive, scanType)
            except Exception,e:
                if Error.OS_Error in e:
                    Log.error("Disk[%s] Has Not Enough Space!"%diskPath)
                    self.mainService.diskState[diskPath] = 1
                else:
                    import traceback
                    Log.error(traceback.format_exc())
                    
            Log.info('ScanFolder[%s] end cost: %d s'%(scanPath, (UtilFunc.Now() - start_time)/1000))
        self.folders[diskPath]['folders'] = []
        build_time = UtilFunc.Now()
        self._delNotExistImageThumb(diskPath)
        Log.info('WipeThunmbNail end cost: %d s'%((UtilFunc.Now() - build_time)/1000))            
        self.mainService.diskState[diskPath] = 0
        Command.ledFlash(2, None) #扫盘结束，状态灯置蓝
        self.folders[diskPath]['status'] = STATUS_STOP
        Log.info('ScanDisk[%s] end!'%diskPath)
        ProfileFunc.RefreshPicturesList()
        
    def scanMoniter(self):
        while True:
            for key in self.folders.keys():
                scan_obj = self.folders[key]
                if scan_obj['status'] != STATUS_WORK and len(scan_obj['folders']) > 0:
                    scan_obj['status'] = STATUS_WORK
                    self.status = STATUS_WORK
#                     import multiprocessing
#                     multiprocessing.freeze_support()
#                     sub_process = multiprocessing.Process(target=self._buildScanFolder,args=(key,scan_obj['recursive'],),name=key)
#                     sub_process.start()
                    sub_thread = threading.Thread(target=self._buildScanFolder,args=(key,scan_obj['recursive'],),name=key)
                    sub_thread.start()
            
            if self._isAllDiskScaned(): self.status = STATUS_IDLE
                    
            time.sleep(2)
    
    def addFolder(self, path, scanType, recursive=False):
        disk = UtilFunc.getDiskPath(path)
        if not disk: return
        self._initMediaFolder(disk, [], STATUS_IDLE, recursive)
        if not path in self.folders[disk]['folders']:
            self.folders[disk]['folders'].append({'folder':path, 'type':scanType})
        
    def removeFolder(self, path):
        disk = UtilFunc.getDiskPath(path)
        if not disk: return 
        if self.folders.has_key(disk):
            for item in self.folders[disk]['folders']:
                if item['folder'] == path:
                    self.folders[disk]['folders'].remove(item)
    
    def getMediaFolder(self, params):
        folder = params.get('folder', '')
        orderBy = params.get('orderBy', 'isFolder desc')
        fileType = params.get('fileType', None)
        limit = int(params.get('limit', -1))
        offset = int(params.get('offset', 0))
        if fileType and not fileType in PopoConfig.filters.keys():
            raise cherrypy.HTTPError(460, 'Bad Parameter') 
        if not ProfileFunc.GetBoxDisks():
            raise cherrypy.HTTPError(465, 'Not Exist Disk')  
        if not folder:
            filelist = ProfileFunc.GetBoxDisks()
        else:
            if UtilFunc.isWindowsSystem(): folder = UtilFunc.formatPath(folder)
            if not os.path.exists(folder):
                raise cherrypy.HTTPError(464, 'Not Exist')
            if os.path.isfile(folder):
                raise cherrypy.HTTPError(460, 'Bad Parameter')
            filelist = os.listdir(folder)
        
        result = ProfileFunc.execConfDbSqlbyPath(folder, 'select url, type from mediafolder', None)
        if not result: selFolders = {}
        else:
            selFolders = {(UtilFunc.getDiskPath(folder) + UtilFunc.toLinuxSlash(f['url'])):f['type'].lower() for f in result}
        files = []
        for onefile in filelist:
            fileInfo = {}
            fileFullPath = UtilFunc.toLinuxSlash(os.path.join(folder, onefile))
            if UtilFunc.isHiddenFile(fileFullPath):
                continue
            if os.path.isfile(fileFullPath) and fileType:
                if not UtilFunc.matchFilter(onefile, filters[fileType]):
                    continue
            fileInfo['folder'] = UtilFunc.toLinuxSlash(fileFullPath)
            fileInfo['type'] = 'all'
            fileInfo['isAdd'] = '0'
            
            if os.path.isdir(fileFullPath):
                fileInfo['isFolder'] = '1'
                if fileFullPath in selFolders.keys():
                    fileInfo['isAdd'] = '1'
                    if UtilFunc.isWindowsSystem():
                        fileInfo['type'] = selFolders[unicode(fileFullPath)]
                    else:
                        fileInfo['type'] = selFolders[fileFullPath.encode('utf8')]
            else:
                fileInfo['isFolder'] = '0'
                par_path = os.path.dirname(fileFullPath)   
                if par_path in selFolders.keys():
                    fileInfo['isAdd'] = '1'

            label_name = ProfileFunc.get_label_name(fileFullPath)
            if label_name:
                fileInfo['name'] = os.path.basename(label_name)
            else:
                fileInfo['name'] = os.path.basename(fileFullPath)
            files.append(fileInfo)
        
        if orderBy:
            cmpInfo = UtilFunc.httpArgToCmpInfo(orderBy)
            files.sort(lambda x,y: UtilFunc.dictInfoCmp(x, y, cmpInfo))    
            
        if limit >= 0:
            files = files[offset:(limit+offset)]
        else:
            files = files[offset:]
            
        ret = {}
        ret['folders'] = files
        ret['offset'] = offset
        ret['limit'] = len(files)

        return ret
    
    def setMediaFolder(self, paths, delpaths):
        for thread_x in set(threading.enumerate()):
            if isinstance(thread_x, scanFolderCtrl):
                thread_x.stop(True)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
        def yield_path(all_path, flag= True):
            for path_a in all_path:
                if not path_a: continue
                if flag: path = UtilFunc.toLinuxSlash(path_a['folder'])
                else: path = UtilFunc.toLinuxSlash(path_a)
                if not os.path.exists(path) or not os.path.isdir(path):
                    continue
                if flag: yield json.dumps(path_a)
                else: yield path 

        scan_set = set(yield_path(paths))
        del_set = set(yield_path(delpaths, False))
        scan_thread = scanFolderCtrl(del_set, scan_set)
        scan_thread.start() 
        return {"path_num": len(paths), "del_num": len(del_set)}
        
    def start(self):
        self.status = STATUS_WORK
        for disk in ProfileFunc.GetBoxDisks(False):
#             folders = ProfileFunc.execConfDbSqlbyPath(disk, 'select url, type from mediafolder')
#             if not folders: 
#                 if UtilFunc.isWindowsSystem():
#                     picFolder = ProfileFunc.GetPictureFolder()
#                     if self.folders.has_key(disk): continue
#                     self._initMediaFolder(disk, [{'folder':picFolder,'type':'all'}], STATUS_IDLE, True)
#                 else:
#                     self._initMediaFolder(disk, [{'folder':disk,'type':'all'}], STATUS_IDLE, True)
#             else:
#                 scanFolders = [{'folder':disk + folderInfo['url'].replace('\\','/').replace('//','/'),'type':folderInfo['type']} for folderInfo in folders]
#                 self._initMediaFolder(disk, scanFolders, STATUS_IDLE, False)
            self._initMediaFolder(disk, [{'folder':disk,'type':'all'}], STATUS_IDLE, True)
        thread.start_new_thread(self.scanMoniter,())

