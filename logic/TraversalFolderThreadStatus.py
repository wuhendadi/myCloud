# -*- coding: utf-8 -*-

import time
import threading
import UtilFunc
import ProfileFunc
import Log

TIMEOUT = 600

class TraversalFolderThreadStatus(threading.Thread):
    def __init__(self, _traversalInfo, _traversakMap):
        threading.Thread.__init__(self)
        self.traversalInfo = _traversalInfo
        self.traversakMap = _traversakMap
        
    def run(self):
        id = self.traversalInfo['id']
        self.checkStatus(id)
        
    def checkStatus(self, id):
        while True:
            time.sleep(5)
            lastTime = self.traversalInfo['lastTime']
            curTime = int(time.time())
            durTime = curTime - lastTime
            if self.traversalInfo['finished'] == 1:
                break
            if durTime >= TIMEOUT:
                Log.error('...lastTime = %d, durTime = %d'%(lastTime, durTime))
                if self.traversalInfo['finished'] == 0:
                    self.traversakMap[id]['finished'] = 1
                    del self.traversakMap[id]
                    ProfileFunc.delTraversalCacheDB(id)
                    break
                else:
                    Log.debug('check status finished!!!!')
                    break

                            