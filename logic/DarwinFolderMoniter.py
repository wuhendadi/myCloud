# -*- coding: utf-8 -*-

import threading
import time
import os
import UtilFunc
import pyinotify
import traceback
import Log

class FolderNotifier(pyinotify.ProcessEvent):
    def __init__(self, _moniter):
        self.moniter = _moniter
    
    def process_default(self, event):
        self.moniter._fileChanged(event.path)

class FolderMoniter(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, name='FolderMoniter')
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, FolderNotifier(self))
        self.notifier.start()
        self.folder2WaitObjMap = {}
        self.delayTime = 2000
        self.changeFolders = {}
        self.checkTimeoutEvent = threading.Event()
        self.mutex = threading.Lock()
        self._getAllWaitObject()
        
    def _fileChanged(self, path):
        self.mutex.acquire()
        if path not in self.changeFolders:
            self.changeFolders[path]=time.time()
        self.mutex.release()
        self.checkTimeoutEvent.set()
    
    def notifyConfigChanged(self):
        self.mutex.acquire()
        self._getAllWaitObject()
        self.mutex.release()
    
    def _getAllWaitObject(self):
        allFolders = self.moniterOwner.getAllMoniterFolders()
        for folderPath in allFolders:
            if not os.path.exists(folderPath):
                continue
            
            if folderPath in self.folder2WaitObjMap:
                continue
            
            mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE
            if self.moniterWrite:
                mask = filter | pyinotify.IN_MODIFY | \
                                pyinotify.IN_ATTRIB

            wdd = self.wm.add_watch(folderPath, mask, rec=True)
            Log.debug('FindFirstChangeNotification:'+repr(folderPath))
            self.folder2WaitObjMap[folderPath] = wdd
        
        delObjects = dict((k, v) for k, v in self.folder2WaitObjMap.iteritems() if k not in allFolders)
        for key in delObjects:
            wdd = self.folder2WaitObjMap[key]
            self.wm.rm_watch(wdd.values())
            del self.folder2WaitObjMap[key]

    def _checkTimeout(self, folder, changeFolders):
        lastChangeTime = changeFolders[folder]
        now = time.time()
        timeDiff = int((now - lastChangeTime) * 1000)
        
        if  timeDiff >= self.delayTime:
            self.moniterOwner.folderChanged(folder)
            return True
        else:
            changeFolders[folder] = time.time()
            return False

    def run(self):
        while UtilFunc.programIsRunning() :
            try:
                if len(self.changeFolders) == 0 :
                    self.checkTimeoutEvent.wait()
                else:
                    self.checkTimeoutEvent.wait(float(self.delayTime)/1000)
                self.checkTimeoutEvent.clear()
            except:
                Log.error(traceback.format_exc())
            
            self.mutex.acquire()
            delFolders = []
            for folder in self.changeFolders:
                if self._checkTimeout(folder, self.changeFolders):
                    delFolders.append(folder)
            
            for folder in delFolders:
                del self.changeFolders[folder]
            self.mutex.release()
                    
