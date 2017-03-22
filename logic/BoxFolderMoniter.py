# -*- coding: utf-8 -*-

import os
import time
import threading
import pyinotify
import PopoConfig
import UtilFunc
import ProfileFunc
import Log

class FolderNotifier(pyinotify.ProcessEvent):
    def __init__(self, _moniter):
        self.moniter = _moniter
    
    def process_default(self, event):
        self.moniter._fileChanged(event)

class FolderMoniterThread(threading.Thread):
    def __init__(self, disk, folderId):
        threading.Thread.__init__(self, name = disk)
        self.disk = disk
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, FolderNotifier(self))
        self.notifier.start()
        self.mutex = threading.Lock()
        self.folderId = folderId
        self._stop = threading.Event()  
        self.mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM
        for root, sub, files in os.walk(disk):
            if not ".popoCloud" in root or not ".cameraApp" in root: 
                self.wm.add_watch(root, self.mask)
    
    def stop(self):
        self.notifier.stop()   
        self._stop.set()  
    
    def stopped(self):         
        return self._stop.isSet() 

    def _fileChanged(self, event):
        Log.info("Received an FileChanged Message[%s : %s]"%(event.path, event.name))               
        if event.name == '.popoCloud' or os.path.basename(event.path) == '.popoCloud':
            if event.mask & pyinotify.IN_DELETE:
                Log.debug(".popoCloud had been deleted! Reset it!")   
                #ProfileFunc.addSubLibrary(self.disk)
                for sub_path in ProfileFunc.getMediaFolder(self.disk):
                    ProfileFunc.addToLibrary(sub_path, False)
            else:
                return
        
        if event.name == '.cameraApp' or os.path.basename(event.path) == '.cameraApp':
            if event.mask & pyinotify.IN_DELETE:
                pass
            else:
                return
        
        popopath = os.path.join(self.disk, '.popoCloud')
        
        dirpath = event.path[0:len(popopath)]
        if str(dirpath) == popopath:
            return
        if event.name.startswith(".popo") or event.name.startswith(".tmp_"):
            return
        
        cameraAppPath = os.path.join(self.disk, '.cameraApp')
        dirpath = event.path[0:len(cameraAppPath)]
        if str(dirpath) == cameraAppPath:
            return
        if event.name.startswith(".camera") or event.name.startswith(".tmp_"):
            return
        
        self.mutex.acquire()

        path = os.path.join(event.path, event.name)
        path = unicode(path)
        
        if event.mask & pyinotify.IN_CREATE:
            if os.path.isdir(path):
                Log.info("AddDir: [%s] To WatchManage" % path)
                self.wm.add_watch(path, self.mask, rec=True)
                
        elif event.mask & pyinotify.IN_CLOSE_WRITE or event.mask & pyinotify.IN_MOVED_TO:
            if os.path.isdir(path):
                Log.info("addDir: [%s] To WatchManage" % path)
                self.wm.add_watch(path, self.mask, rec=False)
                if ProfileFunc.isMediaFolder(path):
                    ProfileFunc.addToLibrary(path, False)
            else:
                Log.info("AddFile: [%s] to Cache" % path)
                ProfileFunc.addFileCache(path)
            
        elif event.mask & pyinotify.IN_DELETE or event.mask & pyinotify.IN_MOVED_FROM:
            Log.info("DelFileCache : [%s]" % path)
            ProfileFunc.removeFolderCache(path)
            ProfileFunc.delFileCache(path)
                  
        self.mutex.release()
        
class FolderMoniter(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self, name='FolderMoniter')
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, FolderNotifier(self))
        self.notifier.start()
        self.delayTime = 2000
        self.changeFolders = {}
        self.checkTimeoutEvent = threading.Event()
        self._stop = threading.Event()
        self.mutex = threading.Lock()
        self.mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE
        if PopoConfig.Hardware == '1.0':
            self.wdd = self.wm.add_watch("/mnt/disks", self.mask, rec=False)
        elif PopoConfig.BoardSys == 'android':
            for disk in [a for a in os.listdir('/mnt') if a.startswith('usbhost')]:
                print disk
                self.wm.add_watch('/mnt/'+ disk, self.mask, rec=True)
        else:
            self.wdd = self.wm.add_watch("/popobox", self.mask, rec=False)
            for disk in os.listdir('/popobox'):
                self.wm.add_watch('/mnt/'+ disk, self.mask, rec=True)
        self.threads = {}
    
    def stop(self):
        for disk in self.threads.keys():
            self.stop_subThreads(disk)
        self.notifier.stop()       
        self._stop.set()
        
    def stop_subThreads(self, disk):
        if disk and self.threads.has_key(disk):
            self.threads[disk].stop()
            Log.info("[%s]FolderMoniterThread Stop!"%disk)
            del self.threads[disk]
            
    def stopAllThreads(self):
        for thread in self.threads.keys():
            self.threads[thread].stop()
            del self.threads[thread]

    def addDisk(self, folderPath, folderId=None):
        if not os.path.exists(folderPath):
            return
        if not self.threads.has_key(folderPath):
            self.threads[folderPath] = FolderMoniterThread(folderPath, folderId)
            Log.info("Start New FolderMoniterThread: [%s]"%folderPath)
            self.threads[folderPath].start()
        
    def waitDiskMounted(self, path):
        while os.path.exists(path):
            if os.listdir(path):
                Log.info("Disk: [%s] mounted!"%path)
                return True
            time.sleep(0.5)
        Log.info("Disk: [%s] Can't Be mounted!"%path)
        return False
        
    def _fileChanged(self, event):
        self.mutex.acquire() 
        try:
            if PopoConfig.Hardware == '1.0':
                if event.path == "/mnt/disks":
                    disk = os.path.join(event.path, event.name)
                    if event.mask & pyinotify.IN_CREATE:
                        Log.info(disk + " addToLibrary")   
                        #ProfileFunc.addSubLibrary(disk)
                        for sub_path in ProfileFunc.getMediaFolder(disk):
                            ProfileFunc.addToLibrary(sub_path, False)
                    elif event.mask & pyinotify.IN_DELETE:
                        Log.info(disk + " StopSubTread")
                        self.stop_subThreads(disk)
                        Log.info(disk + " DeleteRootDir")
                        self.moniterOwner.DeleteRootDir(disk)
            elif PopoConfig.BoardSys == 'android':
                if event.path.startswith("/mnt/usbhost") and len(event.path) == 13:
                    if event.mask & pyinotify.IN_CREATE:
                        disks = UtilFunc.getAndroidMountPaths(event.name)
                        for path in disks: 
                            if not self.waitDiskMounted(path): return
                            Log.info("AddToLibrary: [%s]"%path) 
                            #ProfileFunc.addSubLibrary(path)
                            ProfileFunc.addToLibrary(path, False)
                            
                    elif event.mask & pyinotify.IN_DELETE:
                        for path in self.threads.keys():
                            if event.name in path:
                                Log.info("StopSubTread: [%s]"%path)
                                self.stop_subThreads(path)
                                Log.info("DeleteRootDir: [%s]"%path)
                                ProfileFunc.deleteRootDir(path)
                
            else:
                if event.path == "/popobox":
                    if event.mask & pyinotify.IN_CREATE:
                        path = os.path.join("/mnt",event.name)
                        self.wm.add_watch(path, self.mask, rec=False)
                        
                    elif event.mask & pyinotify.IN_DELETE:
                        for path in self.threads.keys():
                            if event.name in path:
                                Log.info("StopSubTread: [%s]"%path)
                                self.stop_subThreads(path)
                                Log.info("DeleteRootDir: [%s]"%path)
                                ProfileFunc.deleteRootDir(path)
                                
                elif "/mnt/disk" in event.path:
                    path = os.path.join(event.path, event.name)   
                    if event.mask & pyinotify.IN_CREATE:
                        if not self.waitDiskMounted(path): return
                        Log.info("AddToLibrary: [%s]"%path) 
                        ProfileFunc.addSubLibrary(path)
#                         for sub_path in ProfileFunc.getMediaFolder(path):
#                             ProfileFunc.addToLibrary(sub_path, False)
                        ProfileFunc.addToLibrary(path, False)
        except Exception,e:
            Log.error("FolderMoniter Error! Reason:[%s]"%e)
            
        self.mutex.release()
                    
    def notifyConfigChanged(self):
        pass



class usbhostMoniter(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self, name='usbhostMoniter')
        self.targets   = [a for a in os.listdir('/' + PopoConfig.MntName) if a.startswith(PopoConfig.UsbRoot)]
        self.targets.append('sata')
        self.currdisks = []
        self.threads   = {}
        
    def waitDiskMounted(self, path):
        while os.path.exists(path):
            if os.listdir(path):
                Log.info("Disk: [%s] mounted!"%path)
                return True
            time.sleep(0.5)
        Log.info("Disk: [%s] Can't Be mounted!"%path)
        return False
    
    def addDisk(self, folderPath, folderId=None):
        if not os.path.exists(folderPath):
            return
        if not self.threads.has_key(folderPath):
            self.threads[folderPath] = FolderMoniterThread(folderPath, folderId)
            Log.info("Start New FolderMoniterThread: [%s]"%folderPath)
            self.threads[folderPath].start()
    
    def run(self):
        self.currdisks = []
        while True:
            for mountnode in self.targets:
                usbparts = UtilFunc.getAndroidMountPaths(mountnode)
                if usbparts:
                    for partpath in usbparts:
                        if not partpath in self.currdisks:
                            if not self.waitDiskMounted(partpath): return
                            self.currdisks.append(partpath)
                            Log.info('Add usbhost[%s]'%partpath)
                            ProfileFunc.addToLibrary(partpath, False)
                else:
                    for partpath in self.currdisks:
                        ret = UtilFunc.comparePath(partpath, mountnode)
                        if ret == 0 or ret == 1:
                            self.currdisks.remove(partpath)
                            Log.info('Remove usbhost[%s]'%partpath)
                            ProfileFunc.removeFromLibrary(partpath)
            time.sleep(2)