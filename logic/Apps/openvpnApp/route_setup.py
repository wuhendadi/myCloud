#!/usr/bin/env python
import subprocess
import socket
import struct 
import fcntl 
import re
import logging
from openvpn_error import *

OPENVPN_PORT=1194
SS5_PORT=1080
portInfo={}
logger=logging.getLogger("openvpn")

def getLocalIp():
    """
    Returns the actual ip of the local machine.
    This code figures out what source address would be used if some traffic
    were to be sent out to some well known address on the Internet. In this
    case, a Google DNS server is used, but the specific address does not
    matter much.  No traffic is actually sent.
    """
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except socket.error:
        return "None"


def getLocalIpByDev(ethname):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24])   
    
def setupPortInfo(portNum,protocol):
    portInfo['ip']=getLocalIp()
    portInfo['port']=portNum
    portInfo['exPort']=portNum+30000
    portInfo['protocol']=protocol
    return portInfo

def upnpcAddPortRedirection(portInfo):
    logger.info('...upnpc add port redirection %s' % portInfo)
    ip=portInfo['ip']
    port=portInfo['port']
    exPort=portInfo['exPort']
    protocol=portInfo['protocol']
    tryTimes=0
    while True:
        #upnpc [options] -a ip port external_port protocol [duration]
        cmd=['upnpc','-a',ip,str(port),str(exPort),protocol]
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE)
        output, err = p.communicate()
        #AddPortMapping(1194, 1194, 192.168.11.103) failed with code 718 (ConflictInMappingEntry)
        #external 192.168.1.23:1197 TCP is redirected to internal 192.168.11.103:1194 (duration=0)
        #sendto: Network is unreachable
        #No IGD UPnP Device found on the network !
        outputList=output.split('\n')
        upnpcError='Unknown'
        upnpcResult=''
        tryTimes=tryTimes+1
        if tryTimes>10:
            raise GerneralError(generalErrors[5])
            break
        logger.info('try:%d-%s' % (tryTimes,portInfo))
        success_output=' is redirected to internal '+ip+':'+str(port)
        for upnpData in outputList:
            if(re.search('sendto: Network is unreachable',upnpData)):
                upnpcError="NetworkUnreachable" 
                break
            if(re.search('ConflictInMappingEntry',upnpData)):
                upnpcError="PortConflict"
                break
            if(re.search(success_output,upnpData)):
                upnpcError='None'
                upnpcResult=upnpData
                break
        if upnpcError=='NetworkUnreachable':
            logger.warn('Network is unreachable')
            raise GerneralError(generalErrors[3])
            break
        if upnpcError=='PortConflict':
            exPort=exPort+1
            portInfo['exPort']=exPort
            continue
        if upnpcResult.find(ip+':'+str(port))>=0:
            portInfo['exPort']=exPort
            logger.info('redirection port success: %s' % portInfo)
            break
        if upnpcError=='Unknown':
            logger.warn('Route Unkown Error')
            raise GerneralError(generalErrors[6])
            break
    return portInfo

def upnpcDelPortRedirection(portInfo):
    logger.info('...upnpc delete port redirection %s' % portInfo)
    ip=portInfo['ip']
    port=portInfo['port']
    exPort=portInfo['exPort']
    protocol=portInfo['protocol']
    #upnpc [options] -d external_port protocol [port2 protocol2] [...] 
    cmd=['upnpc','-d',str(exPort),protocol]
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    output, err = p.communicate()
    outputList=output.split('\n')
    upnpcError=''
    upnpcResult=''
    for upnpData in outputList:
        if(re.search('sendto: Network is unreachable',upnpData)):
            upnpcError="NetworkUnreachable" 
            break
        if(re.search('UPNP_DeletePortMapping',upnpData)):
            upnpcResult=upnpData
    logger.info(upnpcResult)
    if upnpcError=='NetworkUnreachable':
        logger.warn('Network is unreachable')
    if upnpcResult.find('returned : 0')>=0:
        logger.info('delete port success: %s' % portInfo)
    return portInfo
    
def upnpcListPorRedirection():
    curIp=getLocalIp()
    cmd=['upnpc','-l']
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    output, err = p.communicate()
    outputList=output.split('\n')
    ipData='->'+curIp.strip()
    openPort=[]
    for upnpData in outputList:
        if(re.search(curIp,upnpData)): 
            openPort.append(upnpData)
    logger.info(openPort)
    return openPort

def add_openvpn_port():
    try:
        portInfo=upnpcAddPortRedirection(setupPortInfo(OPENVPN_PORT,'tcp'))
    except Exception,e:
        logger.error(str(e))
        if hasattr(e, 'value'):
            return e.value, None
        else:
            return generalErrors[6], None
    else:
        return True, portInfo 
    
def del_openvpn_port(portInfo):
    try:
        upnpcDelPortRedirection(portInfo)
    except Exception,e:
        logger.error(str(e))
        if hasattr(e, 'value'):
            return e.value
        else:
            return generalErrors[6]
    else:
        return True

def setup_relay_info():
    portInfo['ip']='relay_ip'
    portInfo['port']=OPENVPN_PORT
    portInfo['exPort']=OPENVPN_PORT
    portInfo['protocol']='tcp'
    return portInfo

def main():
    upnpcAddPortRedirection(setupPortInfo(OPENVPN_PORT,'tcp'))

if __name__ == '__main__':
    main()
