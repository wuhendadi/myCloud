import os
import time
import threading
import pyinotify
import PopoConfig
import ProfileFunc
import Log
import thread
import CameraUtils

class CameraFolderNotifier(pyinotify.ProcessEvent):
    def __init__(self, _monitor):
        self.monitor = _monitor
    
    def process_default(self, event):
        self.monitor._fileChanged(event)

class CameraFolderMonitorThread(threading.Thread):
    def __init__(self, disk, folderId):
        threading.Thread.__init__(self, name = disk)
        self.disk = disk
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, CameraFolderNotifier(self))
        self.notifier.start()
        self.mutex = threading.Lock()
        self.folderId = folderId
        self._stop = threading.Event()  
        self.mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM
        for root, sub, files in os.walk(disk):
            Log.info("CameraFolderMonitorThread=>root==>[%s]"%root)
            self.wm.add_watch(root, self.mask)
    
    def stop(self):
        self.notifier.stop()   
        self._stop.set()  
    
    def stopped(self):         
        return self._stop.isSet() 

    def _fileChanged(self, event):
        Log.info("CameraFoldermonitorThread Received an FileChanged Message[%s : %s]"%(event.path, event.name))               

        if event.name.startswith(".popo") or event.name.startswith(".tmp_"):
            return
       
        self.mutex.acquire()

        path = os.path.join(event.path, event.name)
        path = unicode(path)
        
        if event.mask & pyinotify.IN_CREATE:
            if os.path.isdir(path):
                Log.info("CameraFoldermonitorThread AddDir: [%s] To WatchManage" % path)
                self.wm.add_watch(path, self.mask, rec=True)
                
        elif event.mask & pyinotify.IN_CLOSE_WRITE or event.mask & pyinotify.IN_MOVED_TO:
            if os.path.isdir(path):
                Log.info("CameraFoldermonitorThread addDir: [%s] To WatchManage" % path)
                self.wm.add_watch(path, self.mask, rec=False)
            else:
                Log.info("CameraFoldermonitorThread AddFile: [%s] to Cache" % path)
                CameraUtils.addCameraFileCache(path)
            
        elif event.mask & pyinotify.IN_DELETE or event.mask & pyinotify.IN_MOVED_FROM:
            Log.info("DelFileCache : [%s]" % path)
            CameraUtils.delCameraDBWithUrl(path)
                  
        self.mutex.release()

class CameraFolderMonitor:
    def __init__(self):
        pass

    def start(self):
        Log.info("CameraFolderMonitor==start==>>")
        try:
            thread.start_new_thread(self.scanMonitor,())
        except Exception, e:
            Log.exception("CameraFolderMonitor==start==>> failed!!! reason [%s]"%e)

    def scanMonitor(self):
        Log.info("scanMonitor==start==>>")
        recordPath = ProfileFunc.getRecordPath()
        monitorPath = os.path.join(self.record_path, SAVE_PATH)
        monitorThread = CameraFolderMonitorThread(monitorPath, None)
        Log.info("_initFileMonitor Start New FolderMonitorThread: [%s]"%monitorPath)
        monitorThread.start()
        while True:                   
            time.sleep(2)        
        