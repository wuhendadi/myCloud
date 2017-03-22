# -*- coding: utf-8 -*-
#author: ZJW

import PopoConfig
import uuid
import Log

if PopoConfig.Hardware == "1.0":
    from lib import miniupnpc
else:
    import miniupnpc


class UpupPunch:
    
    def __init__(self, sn=uuid.uuid4()):
        self.sn      = sn
        self.natip   = ''
        self.natport = {}
        self.upnpc   = miniupnpc.UPnP()
        self.upnpc.discoverdelay = 5000
        
    def _getName(self, port, name='upnp'): 
        return name + '(' + str(self.sn)[-4:] + ')'
        
    def _isNatPortValid(self, port, name, upnpType='TCP'):
        nat_port = self.natport.get(str(port),None)
        if not nat_port: return False
        r = self.upnpc.getspecificportmapping(int(nat_port), upnpType)
        if r and self._getName(port, name) in r:
            return True 
        return False
    
    def removePortMapping(self, ports, upnpType='TCP'):
        for port in ports:
            if not port: continue
            ret = self.upnpc.getspecificportmapping(int(port), upnpType)
            if not ret: return
            self.upnpc.deleteportmapping(int(port), upnpType)
            for (k, v) in self.natport.items():
                if int(v) == int(port):
                    del self.natport[k]
    
    def addPortMapping(self, port, localIp, localPort, name, upnpType='TCP'):
        try:
            r = self.upnpc.getspecificportmapping(port, upnpType)
            while r != None and port < 65536:
                if self._getName(localPort, name) in r:
                    self.upnpc.deleteportmapping(port, upnpType)
                    break
                else:
                    port = port + 1
                    r = self.upnpc.getspecificportmapping(port, upnpType)
                    
            
            self.upnpc.addportmapping(port, upnpType, localIp, localPort, self._getName(localPort, name), '')
            return str(port)
        except Exception, e:
            Log.debug("UPNP Exception: %s"%e)  
            
    def getUPNPInfo(self, ports, name='Elastos Server', upnpType='TCP'):
        ret = []
        try:
            n = self.upnpc.discover()
            self.upnpc.selectigd()
            localIP = self.upnpc.lanaddr
            externalIP = self.upnpc.externalipaddress()
            
            for portInfo in ports:
                name, port = portInfo.get('name'), portInfo.get('port')
                if self.natip and self.natip == externalIP:
                    if not self._isNatPortValid(port, name, upnpType):
                        self.natport[str(port)] = self.addPortMapping(PopoConfig.upnp_port, localIP, port, name, upnpType)           
                else:
                    self.natip = externalIP
                    self.natport[str(port)] = self.addPortMapping(PopoConfig.upnp_port, localIP, port, name, upnpType) 
                ret.append({'name':name,'port':port,'natPort':self.natport.get(str(port),'')}) 
        except Exception, e:
            Log.error("UPNP Failed! [%s]"%e)
            self.natip = ''
        
        return ret
    
    
    
if __name__ == '__main__':
    upnp = UpnpPunch()
    upnp.getUPNPInfo([{'name':'BoxRelay','port':5000}, {'name':'ClientRelay','port':50001}])
    
