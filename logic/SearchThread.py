# -*- coding: utf-8 -*-

import threading
import os
import UtilFunc
import traceback
import ProfileFunc
import PopoConfig
import Log

class SearchThread(threading.Thread):
    def __init__(self, _searchInfo, _keyword, _folder, _recursive):
        threading.Thread.__init__(self)
        self.searchInfo = _searchInfo
        self.ret = []
        self.keyword = _keyword
        self.recursive = _recursive
        if UtilFunc.isWindowsSystem() and UtilFunc.isSlash(_folder):
            rootDirs = ProfileFunc.getRootFolders()
            rootDirs = UtilFunc.mergeSubFolder(rootDirs, 'url')
            self.folders = []
            for dirInfo in rootDirs:
                self.folders.append(dirInfo['url'])
        else:
            if PopoConfig.Hardware == "1.5" and _folder == '/':
                self.folders = ProfileFunc.GetBoxDisks()
            else:
                self.folders = [_folder]
                
    def _checkFile(self, root, fname, filters, id):
        if self.searchInfo['finished'] != 0: return
        path = os.path.join(root, fname)
        if '.popoCloud' in path: return  
        try:
            statInfo = os.stat(path)
        except:
            return
        name = os.path.basename(path)
        self.searchInfo['path'] = path
        self.searchInfo['fileCount'] += 1
        self.searchInfo['totalSize'] += statInfo.st_size
        
        if not UtilFunc.matchFilter(name, filters): return 
        fileInfo = UtilFunc.formatFileInfo(path)
        if not fileInfo: return
        
        self.ret.append(fileInfo)
        if 32 == len(self.ret):
            ProfileFunc.execInsertSearchDB(id , self.ret)
            self.ret = []
        
    def _searchOneFolder(self, folder, filters, id):
        for root, dirs, files in os.walk(folder, True):
            if self.searchInfo['finished'] != 0: return         
            if not self.recursive and root != folder: continue
            
            self.searchInfo['folder'] = root
            for file in files:
                self._checkFile(root, file, filters, id)
       
            for folder in dirs:
                self._checkFile(root, folder, filters, id)
                
    def run(self):
        filters = self.keyword.split(';')
        success = 1
        searchId = self.searchInfo['id']
        try:
            for folder in self.folders:
                if not UtilFunc.IsMediaInserted(folder):
                    continue
                self._searchOneFolder(folder, filters, searchId)
        except:
            Log.error(traceback.format_exc())
            success = 0
        if 0 != len(self.ret):
            if 0 == self.searchInfo['finished']:
                Log.debug('SearchThread Insert finished')
                ProfileFunc.execInsertSearchDB(searchId , self.ret)
                self.ret = []
            else:
                self.ret = []
        self.searchInfo['success'] = success
        self.searchInfo['finished'] = 1
        Log.debug('SearchThread finished')  
        
