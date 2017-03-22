# -*- coding: utf-8 -*-

import threading
import time
import win32con
import win32event
import win32file
import os
import UtilFunc
import ProfileFunc

import win32api,win32file,time,threading
from win32con import *
import win32security
import win32event

FILE_NOTIFY_CHANGE_CREATION  =   0x00000040

class FolderMoniterThread(threading.Thread):
    def __init__(self, dirPath, folderId, _moniterWrite = True):
        threading.Thread.__init__(self)
        self.dirPath = dirPath
        self.folderId = folderId
        self._stop = threading.Event()  
        self.libraryPath = ProfileFunc.getSubLibraryPath(folderId)
        self.libraryPathLen = 0
        if self.libraryPath: 
            self.libraryPathLen = len(self.libraryPath)
            self.libraryPath = self.libraryPath.lower()
    
    def stop(self):         
        self._stop.set()      
    
    def stopped(self):         
        return self._stop.isSet() 

    def run(self):   
        dirName = self.dirPath
        hdir = win32file.CreateFile(
                dirName,
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                win32security.SECURITY_ATTRIBUTES(),
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS,
                0
            )

        filter = FILE_NOTIFY_CHANGE_FILE_NAME | \
                        FILE_NOTIFY_CHANGE_DIR_NAME \
                        | FILE_NOTIFY_CHANGE_ATTRIBUTES | \
                        FILE_NOTIFY_CHANGE_LAST_WRITE | \
                        FILE_NOTIFY_CHANGE_SIZE
                             
        win32Handle = win32file.FindFirstChangeNotification(dirName,
                                                          True,
                                                          filter)

        while UtilFunc.programIsRunning() :
            results =  win32file.ReadDirectoryChangesW(
                hdir,
                819600,
                True,
                FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_DIR_NAME | \
                FILE_NOTIFY_CHANGE_SIZE | FILE_NOTIFY_CHANGE_LAST_WRITE | \
                FILE_NOTIFY_CHANGE_CREATION,        
#                FILE_NOTIFY_CHANGE_ATTRIBUTES | FILE_NOTIFY_CHANGE_LAST_ACCESS |FILE_NOTIFY_CHANGE_SECURITY
                None,
                None
                )
            
            for action, file in results:
                path = file
                if path == 'Thumbs.db':
                    continue
                
                path = os.path.join(dirName, path)
                path = path.replace('\\', '/')
                if '/.popoCloud/' in path or os.path.basename(path) == '.popoCloud':
                    continue
                
#                print str(action) + " " + path
                
                if action == 1 or action == 5:
                    if os.path.isdir(path):
                        ProfileFunc.addToLibrary(path)
                    else:
                        ProfileFunc.addFileCache(path)
                elif action == 2 or action == 4:
                    ProfileFunc.delFileCache(path)
                elif action == 3:
                    if not os.path.isdir(path):
                        ProfileFunc.delFileCache(path)
                        ProfileFunc.addFileCache(path)
                        
            win32file.FindNextChangeNotification(win32Handle) 
            

class FolderMoniter(object):
    def __init__(self):
        self.configEvent = win32event.CreateEvent(None, 0, 0, None)
        self.threads = {}
        
    def notifyConfigChanged(self):
        win32event.SetEvent(self.configEvent)
        
    def delFolder(self, path):
        if self.threads.has_key(path):
            thread = self.threads.pop(path)
            thread.stop()
    
    def delAllFolder(self):
        for path in self.threads:
            thread = self.threads.pop(path)
            thread.stop()
    
    def stop(self):
        return
        
    def addFolder(self, folderPath, folderId):
        if not os.path.exists(folderPath):
            return
        
        self.threads[folderPath] = FolderMoniterThread(folderPath, folderId)
        self.threads[folderPath].start()
    
    def start(self):
        folderInfos = ProfileFunc.execLibrarySql('select * from folders')
        
        for folderInfo in folderInfos:
            folderId = folderInfo[0]
            folderPath = unicode(folderInfo['path'])
    
            self.addFolder(folderPath, folderId)
