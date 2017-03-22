# -*- coding: utf-8 -*-

import time
import threading
import UtilFunc
import Log

TIMEOUT = 50

class BatchStatusThread(threading.Thread):
    def __init__(self, _operateInfo, operateMap):
        threading.Thread.__init__(self)
        self.operateInfo = _operateInfo
        self.operateMap = operateMap
        
    def run(self):
        id = self.operateInfo['id']
        self.checkStatus(id)
        
    def checkStatus(self, id):
        while True:
            time.sleep(5)
            lastTime = self.operateInfo['lastTime']
            curTime = int(time.time())
            durTime = curTime - lastTime
            if self.operateInfo['finished'] == 1:
                break
            if durTime >= TIMEOUT:
                Log.error('...lastTime = %d, durTime = %d'%(lastTime, durTime))
                if self.operateInfo['finished'] == 0:
                    operateInfo = self.operateMap[id]['info']
                    operateInfo['canceled'] = 1
                    del self.operateMap[id]
                    break
                else:
                    Log.debug('check status finished!!!!')
                    break

                            