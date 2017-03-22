#!/usr/bin/env python

import os
import httplib
import urllib
import urllib2
import subprocess
import logging
import subprocess
import re

testUrlParams = [{'domain': 'icanhazip.com', 'uri': ''}\
                ,{'domain': 'ifconfig.me', 'uri': '/ip'}\
                ,{'domain': 'ipinfo.io', 'uri': ''}\
                ,{'domain': 'whereismyip.com', 'uri': ''}\
                ]

IPv4ranges = {
    '0':                'PUBLIC',   # fall back
    '00000000':         'PRIVATE',  # 0/8
    '00001010':         'PRIVATE',  # 10/8
    '01111111':         'PRIVATE',  # 127.0/8
    '1':                'PUBLIC',   # fall back
    '1010100111111110': 'PRIVATE',  # 169.254/16
    '101011000001':     'PRIVATE',  # 172.16/12
    '1100000010101000': 'PRIVATE',  # 192.168/16
    '111':              'RESERVED', # 224/3
    }

_BitTable = {'0': '0000', '1': '0001', '2': '0010', '3': '0011',
            '4': '0100', '5': '0101', '6': '0110', '7': '0111',
            '8': '1000', '9': '1001', 'a': '1010', 'b': '1011',
            'c': '1100', 'd': '1101', 'e': '1110', 'f': '1111'}
logger=logging.getLogger("ss-server")

def getWanIpInfo():
    logger.info('...get extern network ip')
    for urlParam in testUrlParams:
        logger.info("Test Server : http://" + urlParam['domain'] + urlParam['uri'])
        ip = getRequestIpInfo(urlParam)
        
        if ip is None:
            logger.warn("No ip address found")
        else:
            logger.info("get ip address")
            return ip.strip()
    return None

def getWanIpFromHub():
    return None
    
def getRequestIpInfo(urlParam):
    ip=None
    try:
        con=httplib.HTTPConnection(urlParam['domain'],timeout=10)
        con.request('GET', urlParam['uri'])
        res = con.getresponse()
        if res.status == 200 :
            content = res.read()
            ip=re.search('\d+\.\d+\.\d+\.\d+',content).group(0)
        con.close()
    except Exception, e:
	logger.error(str(e))
    return ip


def _intToBin(val):
    if val < 0:
        print("Only positive values allowed.")
    s = "%x" % val
    ret = ''
    for x in s:
        ret += _BitTable[x]
    # remove leading zeros
    while ret[0] == '0' and len(ret) > 1:
        ret = ret[1:]
    return ret


def _strBin(ipStr):
    bytes=ipStr.split('.')
    if len(bytes)!=4:
        print "IPv4 Address should be 4 bytes."
        return
    bytes += ['0'] * (4 - len(bytes))
    bytes = [int(x) for x in bytes]
    for x in bytes:
        if x>255 or x<0:
            print "single byte error."

    value=(bytes[0] << 24) + (bytes[1] << 16) + (bytes[2] << 8) + bytes[3]
    ret = _intToBin(value)
    return ret


def ipTpye(ipAddr):
    bits=_strBin(ipAddr)
    for i in xrange(len(bits), 0, -1):
        if bits[:i] in IPv4ranges:
            return IPv4ranges[bits[:i]]
    return "unknown"


def getRouteExternalIpAddr():
    ip={} 
    p=subprocess.Popen(["upnpc","-s"],stdout=subprocess.PIPE)
    output, err = p.communicate()
    outputList=output.split('\n')
    for routeData in outputList:
        #Local LAN ip address : 192.168.11.103
        if routeData.find('Local LAN ip address') >=0: 
            tmpDate=routeData.split(':')
	    if len(tmpDate) >=2:
                ip[tmpDate[0].strip()]=tmpDate[1].strip()
        #ExternalIPAddress = 192.168.1.23
        if routeData.find('ExternalIPAddress') >=0:
            tmpDate=routeData.split('=')
	    if len(tmpDate) >=2:
                ip[tmpDate[0].strip()]=tmpDate[1].strip()
    return ip

def main():
    print getWanIpInfo()
    #ip=getRouteExternalIpAddr()

if __name__ == '__main__':
    main()

