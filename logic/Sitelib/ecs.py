# -*- coding = utf-8 -*-
#author:ZJW

import time
import json
import struct
import UtilFunc
import WebFunc
import PopoConfig
import ecs_module
import Log

from constant import *

#from Sitelib import ecs_module

registers=[SHORTURLACK]

class ecsModule:

    def __init__(self):
        self.retdict = {}
        
    def parseData(self, msg, keys=[]):
        (msg,) = struct.unpack(FORMAT_S%len(msg), msg)
        bodyData = json.loads(msg)
        if keys:
            ret = []
            for key in keys:
                ret.append(bodyData.get(key,''))
            return tuple(ret)
        else:
            return bodyData
    
    def online(self, *args, **params):
        Log.info('*********************Box OnLine!************************') 
    
    def offline(self, *args, **params):
        Log.warning('*********************Box OffLine!************************')
    
    def relayReady(self, *args, **params):
        Log.info('*********************Relay Ready!************************') 
    
    def relayDisconnected(self, *args, **params):
        Log.warning('*********************Relay Disconnect!************************') 
    
    def message(self, *args, **params):
        Log.info('*********************Message!************************') 
        return
    
    def hubMessage(self, type=0, msg=''):
        Log.info('Receive HubMessage type[%s]'%type)
            
        if type == SHORTURLACK:
            (shareId,) = self.parseData(msg, ('shareId',))
            if not shareId: return 
            self.retdict[shareId] = self.parseData(msg)
            print self.retdict
            
    def version(self):
        return ecs_module.internal_version()
    
    def start(self): 
        while True:
            result = ecs_module.init(hub_domain=PopoConfig.ServerHost,
                                     hub_port=PopoConfig.ServerPort,
                                     device_sn=UtilFunc.getSN(),
                                     device_name='PopoBox',
                                     device_system='Linux',
                                     device_system_version=PopoConfig.VersionInfo,
                                     device_hardware_version=PopoConfig.Hardware,
                                     log_file='/popoCloudData/log/ecs.log',
                                     log_level=PopoConfig.LogLevel,
                                     test_network_script=None)
            if result != 0:
                Log.error('ECSmodule init failed! ReTry 10s Later!')
                time.sleep(10)
                continue
            
            ecs_module.set_event_handler(online=self.online,
                                         offline=self.offline,
                                         relay_ready=self.relayReady,
                                         relay_disconnected=self.relayDisconnected,
                                         message=self.message,
                                         hub_message=self.hubMessage);
                                        
            
            for messageType in registers:
                ecs_module.register_hub_message(messageType)
                                         
            for server in UtilFunc.getAccessServices():
                ecs_module.add_service(server['name'], 1, None, server['port'])
                
            result = ecs_module.start()
            if result != 0:
                continue
        
