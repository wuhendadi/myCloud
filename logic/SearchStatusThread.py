# -*- coding: utf-8 -*-

import time
import threading
import UtilFunc
import ProfileFunc
import Log

class SearchStatusThread(threading.Thread):
    def __init__(self, _searchInfo, _searchMap):
        threading.Thread.__init__(self)
        self.searchInfo = _searchInfo
        self.searchMap = _searchMap
        
    def run(self):
        sid = self.searchInfo['id']
        self.checkStatus(sid)
        
    def checkStatus(self, sid):
        while True:
            time.sleep(5)
            lastTime = self.searchInfo['lastTime']
            curTime = int(time.time())
            durTime = curTime - lastTime
            if self.searchInfo['finished'] == 1:
                break      
            if durTime >= 600:
                Log.error('...lastTime = %d, durTime = %d'%(lastTime, durTime))
                if self.searchInfo['finished'] == 0:
                    searchMapEntry = self.searchMap[sid]
                    searchInfo = searchMapEntry['info']
                    searchInfo['finished'] = 1
                    del self.searchMap[sid]
                    ProfileFunc.delSearchCacheDB(sid)
                    break
                else:
                    Log.debug('check status finished!!!!')
                    break

                            