import re
import os
import json
import logging
from ip_util import getWanIpInfo
from ip_util import getRouteExternalIpAddr
from ip_util import ipTpye
from ss_error import *

logger=logging.getLogger("ss-server")
CONF_DIR='/etc/shadowsocks'
DEF_CONF='/etc/shadowsocks/config.json'

def generate_client_conf(portInfo):
    global CONF_DIR 
    logger.info('...generate client conf')
    if portInfo['ip']=='relay_ip':
        extern_ip_addr='relay_ip'
    else:
        extern_ip_addr=getWanIpInfo()
    route_ip=getRouteExternalIpAddr()
    if route_ip.has_key('ExternalIPAddress'):
        route_ip_type=ipTpye(route_ip['ExternalIPAddress'])
        if route_ip_type=='PRIVATE':
	    portInfo['ip']='relay_ip'
            extern_ip_addr='relay_ip'
        else:
	    addr_len=len(extern_ip_addr)
	    if cmp(extern_ip_addr[:addr_len-1], route_ip['ExternalIPAddress'][:addr_len-1])==0:
	        extern_ip_addr=route_ip['ExternalIPAddress']
    else:
        logger.info('...can not get route ip')

    if extern_ip_addr is None: 
        logger.info('...can not get extern ip')
        return GerneralError(generalErrors[2]), None
    logger.info('extern ip %s' % extern_ip_addr)

    if os.path.isfile(DEF_CONF):
	old_client_conf=DEF_CONF
        logger.info("default file exist"); 
    else:
        return GerneralError(generalErrors[2]), None

    port=portInfo['exPort']
    protocal='tcp'
    client_conf='ss_'+extern_ip_addr+'_'+protocal+'_'+str(port)+'.conf'
    f_in=open(old_client_conf,'r')
    f_out=open(CONF_DIR+'/'+client_conf,'w')
    js=None
    try:
        js=json.load(f_in)
    except Exception,e:
        logger.info("parse json bad line")

    js["server"]=extern_ip_addr 
    js["server_port"]=port
    f_out.write(json.dumps(js,ensure_ascii=False))

    f_in.close()
    f_out.close()
    return True, client_conf

def check_ss_conf():
    global CONF_DIR 
    if os.path.exists(CONF_DIR):
        pass
    else:
        return None
    return os.listdir(CONF_DIR)

def get_conf_dir():
    global CONF_DIR 
    return CONF_DIR


