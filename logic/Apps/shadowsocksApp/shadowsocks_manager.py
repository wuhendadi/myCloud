#!/usr/bin/env python
import os
import time
import sys
import tempfile
from process_monitor import ProcessMonitor 
from route_setup import add_socks_port
from route_setup import del_socks_port
from route_setup import setup_relay_info
import logging
from gen_conf import generate_client_conf
from gen_conf import check_ss_conf
from gen_conf import get_conf_dir


logger=logging.getLogger("ss-server")
class SsManager():
    def __init__(self,settings):
        # Initialise the parent class
        self.settings=settings
        self.conf=None
        self.tmp_folder= os.path.join(tempfile.gettempdir(), 'shadowsocks')
        self.ss_cmd="/system/bin/ss-server -c /etc/shadowsocks/config.json"
        self.settings['APP']='ss_server'
        self.settings['CMD']=self.ss_cmd.split()
        self.settings['PIDFILE']=self.tmp_folder+'/ss_server.pid'
        self.settings['LOG']=self.tmp_folder+'/ss_server.log'
        self.settings['TMP']=self.tmp_folder+'/ss_server.tmp'
        self.ssMgr=ProcessMonitor(settings) 
        self.__do_init()
	logger=logging.getLogger("ss-server")
	logger.setLevel(logging.DEBUG)
	formatter=logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
	file_handler = logging.FileHandler(self.settings['LOG'])
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
        self.portInfo={}

    def start(self):
        logger.info('...shadowsocks start')
        self.ret, self.portInfo=add_socks_port()
        if self.ret is not True:
	    logger.info('Added upnp port failed')
	    self.portInfo=setup_relay_info()

        self.ret, self.conf=generate_client_conf(self.portInfo)
        if self.ret is not True:
            return self.ret[0]
        logger.info('client conf path: %s' % self.get_client_conf())

        if self.ssMgr.start() is True:
            logger.info('...shadowsocks start success')

        return 0

    def stop(self):
        logger.info('...shadowsocks stop')
        self.ret=self.ssMgr.stop()
        if self.portInfo.has_key('exPort'):
            del_socks_port(self.portInfo)
        if self.ret is not True:
            return self.ret[0]
        logger.info('...shadowsocks stop success')

    def check_state(self):
        if self.ssMgr.status() is None:
            return False
        else:
            return True

    def restart(self):
        self.ssMgr.restart()

    def __init_folder(self):
        if not os.path.exists(self.tmp_folder):
            os.makedirs(self.tmp_folder)

    def __is_reboot(self):
        if(os.path.exists(self.tmp_folder)):        
            return False
        else:
            os.mkdir(self.tmp_folder)
            return True 

    def __do_init(self):
        if self.__is_reboot() is True:
           print '...shadowsocks do init'
           self.__init_folder()

    def get_client_conf(self): 
        cert_list=check_ss_conf()
        if self.conf is None:
            return None
        if self.conf in cert_list:
            cert_path=get_conf_dir()+'/'+self.conf
            return cert_path
        else:
            return None
            

def main():
    settings={}
    ssMgr=SsManager(settings)
    ssMgr.start() 
    time.sleep(8)
    #ssMgr.restart() 
    #time.sleep(8)
    ssMgr.stop() 

if __name__ == '__main__':
    main()
