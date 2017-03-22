#!/usr/bin/env python
import os
import time
import sys
import tempfile
from process_monitor import ProcessMonitor 
from gen_cert import *
from route_setup import add_openvpn_port
from route_setup import del_openvpn_port
from route_setup import setup_relay_info
import logging

logger=logging.getLogger("openvpn")
class OpenvpnManager():
    def __init__(self,settings):
        # Initialise the parent class
        self.settings=settings
        self.conf=None
        self.tmp_folder= os.path.join(tempfile.gettempdir(),'openvpn')
        self.openvpn_cmd="/system/bin/openvpn --dev-node /dev/tun --config /etc/openvpn/openvpn_server.conf --tmp-dir %s"%self.tmp_folder
        self.settings['APP']='openvpn_server'
        self.settings['CMD']=self.openvpn_cmd.split()
        self.settings['PIDFILE']=self.tmp_folder+'/openvpn_server.pid'
        self.settings['LOG']=self.tmp_folder+'/openvpn_server.log'
        self.settings['TMP']=self.tmp_folder+'/openvpn_server.tmp'
        self.openvpnMgr=ProcessMonitor(settings) 
        self.__do_init()
	logger=logging.getLogger("openvpn")
	logger.setLevel(logging.DEBUG)
	formatter=logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
	file_handler = logging.FileHandler(self.settings['LOG'])
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
        #logger.basicConfig(level=logger.DEBUG,
        #                format='%(asctime)s %(levelname)-8s %(message)s',
        #                filename=self.settings['LOG'],datefmt='%Y-%m-%d %H:%M:%S', filemode='a+')
        self.portInfo={}
        #self.stop()

    def start(self):
        logger.info('...openvpn start')
        self.ret=cert_init()
        if self.ret is not True:
            return self.ret[0]
        self.ret, self.portInfo=add_openvpn_port()
        if self.ret is not True:
            logger.info('Added upnp port failed')
	    self.portInfo=setup_relay_info()

        self.ret, self.conf=generate_client_conf(self.portInfo)
        if self.ret is not True:
            return self.ret[0]
        logger.info('client conf path: %s' % self.get_client_conf())

        self.ret=self.openvpnMgr.start()

        if self.ret is not True:
            return self.ret[0]

        #if self.portInfo['ip']=='relay_ip':
        #    self.ret=lunch_ecs()

        logger.info('...openvpn start success')
        return 0

  
    def stop(self):
        logger.info('...openvpn stop')
        self.ret=self.openvpnMgr.stop()
        if self.portInfo.has_key('exPort'):
            del_openvpn_port(self.portInfo)
        if self.ret is not True:
            return self.ret[0]
        logger.info('...openvpn stop success')
        return 0

    def restart(self):
        self.openvpnMgr.restart()

    def check_state(self):
        if self.openvpnMgr.status() is None:
            return False
        else:
            return True

    def __insert_tunko(self):
        cmd='insmod /system/lib/tun.ko'
        ret = os.system(cmd)

    def __init_folder(self):
        if not os.path.exists(self.tmp_folder):
            os.makedirs(self.tmp_folder)
        os.system('chmod -R 755 /etc/openvpn') #generate crt in the folder

    def __iptable_setup(self):
        ret =0
        cmd='echo "1" > /proc/sys/net/ipv4/ip_forward'
        ret |= os.system(cmd)
	cmd='iptables -A INPUT -i eth0 -p tcp --dport 1194 -j ACCEPT'
        ret |= os.system(cmd)
        # Allow TUN interface connections to OpenVPN server
        cmd='iptables -A INPUT -i tun+ -j ACCEPT'
        ret |= os.system(cmd)
        # Allow TUN interface connections to be forwarded through other interfaces
        cmd='iptables -A FORWARD -i tun+ -j ACCEPT'
        ret |= os.system(cmd)
        cmd='iptables -A FORWARD -i tun+ -o eth0 -j ACCEPT'
        ret |= os.system(cmd)
        cmd='iptables -A FORWARD -i eth0 -o tun+ -j ACCEPT'
        ret |= os.system(cmd)
        # NAT the VPN client traffic to the internet
        cmd='iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE'
        ret |= os.system(cmd)
        return ret

    def __is_reboot(self):
        if(os.path.exists(self.tmp_folder)):        
            return False
        else:
            os.mkdir(self.tmp_folder)
            return True 

    def __do_init(self):
        if self.__is_reboot() is True:
           print '...openvpn do init'
           if os.path.exists('/dev/tun') is not True:
               self.__insert_tunko()
           self.__iptable_setup()
           self.__init_folder()
            
    def get_client_conf(self): 
        cert_list=check_ovpn_file()
        if self.conf is None:
            return None
        if self.conf in cert_list:
            cert_path=get_key_dir()+'/'+self.conf
            return cert_path
        else:
            return None

    def gen_client_conf(self):
        logger.info('...generate client conf')
        self.ret=cert_init()
        if self.ret is not True:
            return self.ret[0]
        self.ret, self.portInfo=add_openvpn_port()
        if self.ret is not True:
            return self.ret[0]
        self.ret, self.conf=generate_client_conf(self.portInfo)
        if self.ret is not True:
            return self.ret[0]
        logger.info('client conf path: %s' % self.get_client_conf())
        return 0

    def revoke_client(self):
        return revoke_client_crt()
        
def main():
    settings={}
    openvpnMgr=OpenvpnManager(settings)
    openvpnMgr.start() 
    #time.sleep(8)
    #openvpnMgr.restart() 
    time.sleep(8)
    openvpnMgr.stop() 

if __name__ == '__main__':
    main()
