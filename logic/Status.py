# -*- coding = utf-8 -*-

import time
import cherrypy
import socket
import threading
import ProfileFunc
import UtilFunc
import PopoConfig
import Log

STATUS_IDLE = 0
STATUS_COMM = 1
STATUS_BUSY = 2
IDLE_WAIT  = 5*60

class Status:
    
    def __init__(self, parent, upnp):
        self.parent        = parent
        self.parent.status = self
        from relay.src.relay import RelayServer
        self.relay         = RelayServer(upnp)
        self.lock          = threading.Lock()
        self.setStatus(STATUS_IDLE)
        self.listening()
            
    def supplyRelay(self, value=True):
        self.lock.acquire()
        if UtilFunc.toBoolean(PopoConfig.ISRELAY):
            if value and self.status == STATUS_IDLE:
                self.relay.start()
                Log.info('SupplyRelay Started!')
            else:
                self.relay.stop()
                Log.info('SupplyRelay Stopped!')
        else:
            self.relay.stop()
            Log.info('SupplyRelay Stopped!')
        self.lock.release()
    
    def setStatus(self, value):
        self.status = value
        Log.info('*****************PopoBox Status Changed**************************')
        Log.info('Current Status: [%s]'%self.status)
        if self.status == STATUS_IDLE:
            self.supplyRelay(True)
        elif self.status == STATUS_BUSY:
            self.supplyRelay(False)
    
    def listening(self):
        current = None
        while True:
            len_server = len(cherrypy.engine.timeout_monitor.servings)
            if len_server == 0:
                if self.status == STATUS_COMM:
                    self.status = STATUS_IDLE
                elif self.status ==STATUS_BUSY:
                    if not current: 
                        current = time.time()
                    if time.time() - current >= IDLE_WAIT:
                        self.setStatus(STATUS_IDLE)
            elif len_server > 0: 
                if self.status == STATUS_IDLE:
                    self.status = STATUS_COMM
                elif self.status == STATUS_COMM:
                    self.setStatus(STATUS_BUSY)
                    current = None
            else:
                current = None
            time.sleep(2)
        

class broadcast:
    
    def __init__(self):
        self.run()
    
    def run(self):
        if UtilFunc.isWindowsSystem(): return
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)  
        s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)  
        s.bind(('',50000))  
        while True:  
            try:  
                data,addr=s.recvfrom(1024)  
                Log.info("BroadCast got data from[%s]"%addr[0])  
                s.sendto(str(UtilFunc.getWebServerPort()),addr)  
            except Exception,e:
                Log.exception('BroadCast Exception! Reason[%s]'%e)
                continue

    
