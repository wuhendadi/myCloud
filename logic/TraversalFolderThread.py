# -*- coding: utf-8 -*-

import threading
import os
import UtilFunc
import traceback
import ProfileFunc
import PopoConfig
import Log

WRITECOUNT = 32

class TraversalFolderThread(threading.Thread):
    def __init__(self, _traversalInfo, _path):
        threading.Thread.__init__(self)
        self.traversalInfo  = _traversalInfo
        self.ret            = []
        self.paths          = []
        self.paths          = [_path]
        
    def _traversalFolder(self, _path, id):
        for root, dirs, files in os.walk(_path, True):
            if self.traversalInfo['finished'] != 0:
                return         
            self.traversalInfo['folder'] = root
            for f in files:
                if self.traversalInfo['finished'] != 0:
                    return

                path = os.path.join(root, f)
                if '.popoCloud' in path or '.svn' in path:
                    continue

                try:
                    statInfo = os.stat(path)
                except:
                    Log.error(traceback.format_exc())
                    continue

                name = os.path.basename(path)
                
                self.traversalInfo['path']      = path
                self.traversalInfo['fileCount'] += 1
                self.traversalInfo['totalSize'] += statInfo.st_size

                fileInfo = {}
                fileInfo['url']           = UtilFunc.toLinuxSlash(path)
                fileInfo['name']          = name
                fileInfo['contentType']   = UtilFunc.getFileExt(name)
                fileInfo['isFolder']      = 'False'
                fileInfo['ETag']          = UtilFunc.getFileEtag(path)
                fileInfo['contentLength'] = statInfo.st_size
                fileInfo['creationTime']  = int(statInfo.st_ctime * 1000)
                fileInfo['lastModify']    = int(statInfo.st_mtime * 1000)
                
                self.ret.append(fileInfo)
                if WRITECOUNT == len(self.ret):
                    ProfileFunc.execInsertTraversalDB(id , self.ret)
                    self.ret = []
                
            for d in dirs:
                if self.traversalInfo['finished'] != 0:
                    return
                
                path = os.path.join(root, d)
                
                if not UtilFunc.isFolderEmpty(path):
                    continue
                
                if '.popoCloud' in path or '.svn' in path:
                    continue
                
                statInfo                            = os.stat(path)
                name                                = os.path.basename(path)
                self.traversalInfo['folder']        = path
                self.traversalInfo['folderCount']   += 1
                            
                fileInfo = {}
                fileInfo['url']            = path
                fileInfo['name']           = name
                fileInfo['contentType']    = ''
                fileInfo['isFolder']       = 'True'
                fileInfo['ETag']           = UtilFunc.getFileEtag(path)
                fileInfo['contentLength']  = -1
                fileInfo['creationTime']   = int(statInfo.st_ctime * 1000)
                fileInfo['lastModify']     = int(statInfo.st_mtime * 1000)
                
                self.ret.append(fileInfo)
                
                if WRITECOUNT == len(self.ret):
                    ProfileFunc.execInsertTraversalDB(id , self.ret)
                    self.ret = []
                

    def run(self):
        success     = 1
        traversalId = self.traversalInfo['id']
        try:
            for path in self.paths:
                if not UtilFunc.IsMediaInserted(path):
                    continue
                self._traversalFolder(path, traversalId)
        except:
            Log.error(traceback.format_exc())
            success = 0
        if 0 != len(self.ret):
            if 0 == self.traversalInfo['finished']:
                Log.debug('TraversalFolderThread Insert finished')
                ProfileFunc.execInsertTraversalDB(traversalId , self.ret)
                self.ret = []
            else:
                self.ret = []
        self.traversalInfo['success']   = success
        self.traversalInfo['finished']  = 1
        Log.debug('TraversalFolderThread finished')  
        
