#!/usr/bin/env python
import os
#import pexpect
import shutil
import time
import re
from ip_util import getWanIpInfo
from ip_util import getRouteExternalIpAddr
from ip_util import ipTpye
import subprocess, os
import glob
import random
import logging
from openvpn_error import *


SERVER_NAME="server"
CLIENT_NAME="client"
PWD=os.getcwd()
EASY_RSA=PWD
EASY_RSA='/etc/openvpn'
KEY_CONFIG=EASY_RSA+"/openssl.cnf"
KEY_DIR=EASY_RSA+"/keys"

logger=logging.getLogger("openvpn")
def shell_source(script):
    """Sometime you want to emulate the action of "source" in bash,
    settings some environment variables. Here is a way to do it."""
    pipe = subprocess.Popen(". %s; busybox env" % script, stdout=subprocess.PIPE, executable="/system/bin/sh", shell=True)
    output = pipe.communicate()[0]
    env = dict((line.split("=", 1) for line in output.splitlines()))
    os.environ.update(env)

def source_env():
    logger.info('...source env')
    global EASY_RSA
    shell_source(EASY_RSA+'/vars')
    os.environ['EASY_RSA']=EASY_RSA

def touch(fname, times=None):
    with file(fname, 'wa'):
         os.utime(fname, times)
    os.chmod(fname, 0755)

def get_key_dir():
    return KEY_DIR

def clean_keys_dir():
    logger.info('...clean keys dir')
    if os.path.exists(KEY_DIR):
         shutil.rmtree(KEY_DIR)
    os.mkdir(KEY_DIR)
    os.chmod(KEY_DIR,0766)
    touch(KEY_DIR+'/index.txt')
    touch(KEY_DIR+'/serial')
    try:
        serial=open(KEY_DIR+'/serial','w')
        try:
            serial.write('01')
        finally:
            serial.close()
            return True
    except IOError:
        logger.warn("Can't write")
        raise GerneralError(generalErrors[2])
        return False


def build_root_ca():
    logger.info('...build root ca')
    global KEY_DIR
    global KEY_CONFIG
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        raise GerneralError(generalErrors[2])
        return False

    #cmd=OPENSSL req BATCH -days CA_EXPIRE NODES_REQ -new -newkey rsa:$KEY_SIZE -sha1 -x509 -keyout "$CA.key" -out "$CA.crt" -config KEY_CONFIG
    cmd="openssl req -days 3650 -nodes -new -newkey rsa:1024 -sha1 -x509 -keyout ca.key -out ca.crt -config "+KEY_CONFIG
    p=subprocess.Popen(cmd.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.stdin.write('\n') #Country Name (2 letter code) [CH]:
    p.stdin.write('\n') #State or Province Name (full name) [SH]:
    p.stdin.write('\n') #Locality Name (eg, city) [ShangHai]:
    p.stdin.write('\n') #Organization Name (eg, company) [kortide.com]:
    p.stdin.write('\n') #Organizational Unit Name (eg, section) []:
    p.stdin.write('\n') #Common Name (eg, your name or your server's hostname) [kortide.com CA]:
    p.stdin.write('\n') #Name []:
    p.stdin.write('\n') #Email Address [xia.ying@kortide.com]:
    status=p.wait()
    res, err = p.communicate()
    if status==0 :
        os.chmod("ca.key",0600)
        return True
    else:
        raise GerneralError(generalErrors[2])
        return False


def build_key_crt(target):
    logger.info('...build %s key crt' % target)
    global KEY_DIR
    global KEY_CONFIG

    random_name=str(random.randrange(0,1000))
    os.environ['KEY_CN']=target+random_name
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        raise GerneralError(generalErrors[2])
        return False

    global SERVER_NAME
    server_key=SERVER_NAME+'.key'
    server_csr=SERVER_NAME+'.csr'
    server_crt=SERVER_NAME+'.crt'

    global CLIENT_NAME
    client_key=CLIENT_NAME+'.key'
    client_csr=CLIENT_NAME+'.csr'
    client_crt=CLIENT_NAME+'.crt'

   
    if(target=="server"):
        cmd_key="openssl req -days 3650 -nodes -new -newkey rsa:1024 -keyout "+server_key+" -out "+server_csr+" -extensions server -config "+KEY_CONFIG 
        cmd_crt="openssl ca -days 3650 -out "+server_crt+" -in "+server_csr+" -extensions server -md sha1 -config "+KEY_CONFIG
    if(target=="client"):
        #cmd=$OPENSSL req $BATCH -days $KEY_EXPIRE $NODES_REQ -new -newkey rsa:$KEY_SIZE -keyout "$FN.key" -out "$FN.csr" $REQ_EXT -config "$KEY_CONFIG" $PKCS11_ARGS 
        cmd_key="openssl req -days 3650 -nodes -new -newkey rsa:1024 -keyout "+client_key+" -out "+client_csr+" -config "+KEY_CONFIG 
        #$OPENSSL ca $BATCH -days $KEY_EXPIRE -out "$FN.crt" -in "$FN.csr" $CA_EXT -md sha1 -config "$KEY_CONFIG" 
        cmd_crt="openssl ca -days 3650 -out "+client_crt+" -in "+client_csr+" -md sha1 -config "+KEY_CONFIG

    p=subprocess.Popen(cmd_key.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.stdin.write('\n') #Country Name (2 letter code) [CH]:
    p.stdin.write('\n') #State or Province Name (full name) [SH]:
    p.stdin.write('\n') #Locality Name (eg, city) [ShangHai]:
    p.stdin.write('\n') #Organization Name (eg, company) [kortide.com]:
    p.stdin.write('\n') #Organizational Unit Name (eg, section) []:
    p.stdin.write('\n') #Common Name (eg, your name or your server's hostname) 
    p.stdin.write('\n') #Name []:
    p.stdin.write('\n') #Email Address [xia.ying@kortide.com]:
    p.stdin.write('\n') #A challenge password []:
    p.stdin.write('\n') #An optional company name []:
    status=p.wait()
    res, err = p.communicate()

    p=subprocess.Popen(cmd_crt.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.stdin.write('y\n') #Sign the certificate? [y/n]:
    p.stdin.write('y\n') #1 out of 1 certificate requests certified, commit?
    status=p.wait()
    res, err = p.communicate()

    if os.path.isfile(server_key) or os.path.isfile(client_key):
        return True
    else:
        raise GerneralError(generalErrors[2])
        return False

    if os.path.isfile(server_crt) or os.path.isfile(client_crt):
        return True
    else:
        raise GerneralError(generalErrors[2])
        return False

   
def build_dh():
    logger.info('...build dh key')
    global KEY_DIR
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        raise GerneralError(generalErrors[2])
        return False

    key_size=os.environ.get('KEY_SIZE')
    dh_key=KEY_DIR+'/dh'+key_size+'.pem'
    cmd_dh="openssl dhparam -out "+dh_key+' '+key_size

    p=subprocess.Popen(cmd_dh.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    status=p.wait()
    res, err = p.communicate()

    if os.path.isfile(dh_key):
        return True
    else:
        raise GerneralError(generalErrors[2])
        return False

def fast_cp_dh():
    global EASY_RSA
    global KEY_DIR
    src_dh_key=EASY_RSA+'/dh1024.pem'
    dest_dh_key=KEY_DIR+'/dh1024.pem'
    if os.path.isfile(src_dh_key):
        logger.info('...fast cp dh key') 
        shutil.copyfile(src_dh_key,dest_dh_key)
        return True
    else:
        return build_dh()
 
def generate_crl():
    global KEY_DIR
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        raise GerneralError(generalErrors[2])
        return False
    crl_file=KEY_DIR+'/crl.pem'
    cmd='openssl ca -gencrl -out '+crl_file+' -config '+KEY_CONFIG
    p=subprocess.Popen(cmd.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    status=p.wait()
    res, err = p.communicate()

    #show crl list
    cmd='openssl crl -noout -text -in '+crl_file
    p=subprocess.Popen(cmd.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    status=p.wait()
    res, err = p.communicate()
    logger.info(res)

    if os.path.isfile(crl_file):
        return True
    else:
        raise GerneralError(generalErrors[2])
        return False

    
def revoke_client_crt():
    global KEY_DIR
    global CLIENT_NAME
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        raise GerneralError(generalErrors[2])
        return False

    client_crt=KEY_DIR+'/'+CLIENT_NAME+'.crt'
    # revoke key and generate a new CRL
    cmd='openssl ca -revoke '+client_crt+' -config '+KEY_CONFIG
    p=subprocess.Popen(cmd.split(),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    status=p.wait()
    res, err = p.communicate()

    # generate a new CRL
    generate_crl()
    return True
    
def generate_all():
    clean_keys_dir()
    source_env()
    print build_root_ca()   
    print build_key_crt('server')
    print build_key_crt('client')
    #print revoke_client_crt()
    #print build_dh()

def copy_part_file(file_in,output,begin_sign,end_sign):
    begin_copy=0
    with open(file_in) as input: 
         for line in input:
             if line.startswith(begin_sign):
                 begin_copy=1
             if begin_copy==1:
	         output.write(line)
             if line.startswith(end_sign):
                 begin_copy=0
    input.close()

def check_cert_file():
    global KEY_DIR
    if os.path.exists(KEY_DIR):
        pass
    else:
        return None
    return os.listdir(KEY_DIR)
    
def check_client_need():
    global CLIENT_NAME
    files = check_cert_file()
    if files is None:
        return False
    if 'ca.crt' in files and CLIENT_NAME+'.key' in files and CLIENT_NAME+'.crt' in files:
        return True
    else:
        return False

def check_server_need():
    logger.info('...check_server_need')
    global SERVER_NAME
    global KEY_DIR
    files = check_cert_file()
    if files is None:
        return False
    #key_size=os.environ.get('KEY_SIZE')
    dh_key='dh1024.pem'
    if 'ca.crt' in files and SERVER_NAME+'.key' in files and SERVER_NAME+'.crt' in files and dh_key in files:
        return True
    else:
        return False

def check_ovpn_file():
    global KEY_DIR
    if os.path.exists(KEY_DIR):
        pass
    else:
        return None
    ovpn_list=glob.glob('*.ovpn')
    return ovpn_list 
    
def generate_client_conf(portInfo):
    logger.info('...generate client conf')
    global KEY_DIR
    global EASY_RSA 
    global CLIENT_NAME
    if os.path.exists(KEY_DIR):
        os.chdir(KEY_DIR)
    else:
        return GerneralError(generalErrors[2]), None
    if check_client_need() is False:
        return GerneralError(generalErrors[2]), None
    copy_from_file=0
    jump_line=0
    if portInfo['ip']=='relay_ip':
        extern_ip_addr='relay_ip'
    else:
        extern_ip_addr=getWanIpInfo()
    route_ip=getRouteExternalIpAddr()
    if route_ip.has_key('ExternalIPAddress'):
        route_ip_type=ipTpye(route_ip['ExternalIPAddress'])
        if route_ip_type=='PRIVATE':
	    portInfo['ip']='relay_ip'
            #extern_ip_addr=route_ip['ExternalIPAddress']
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

    ca_cert=KEY_DIR+'/ca.crt'
    client_key=KEY_DIR+'/'+CLIENT_NAME+'.key'
    client_crt=KEY_DIR+'/'+CLIENT_NAME+'.crt'
    old_client_conf=EASY_RSA+'/openvpn_client.conf'
    port=portInfo['exPort']
    protocal='tcp'
    client_conf='vpngate_'+extern_ip_addr+'_'+protocal+'_'+str(port)+'.ovpn'
    f_in=open(old_client_conf,'r')
    f_out=open(client_conf,'w')
    for line in f_in:
        if(jump_line == 0):
            if(re.match(r'^remote.*$',line)): #write ip info
                new_ip_info='remote '+extern_ip_addr+' '+str(port)
                f_out.write(new_ip_info)
            else:
                f_out.write(line)
        if re.match(r'^<ca>',line): 
            jump_line=1
        if re.match(r'^</ca>',line): 
            copy_part_file(ca_cert,   f_out,'-----BEGIN CERTIFICATE-----','-----END CERTIFICATE-----')
            jump_line=0
            f_out.write(line)
        if re.match(r'<cert>',line): 
            jump_line=1
        if re.match(r'^</cert>',line): 
            copy_part_file(client_crt,f_out,'-----BEGIN CERTIFICATE-----','-----END CERTIFICATE-----')
            jump_line=0
            f_out.write(line)
        if re.match(r'^<key>',line): 
            jump_line=1
        if re.match(r'^</key>',line): 
            copy_part_file(client_key,f_out,'-----BEGIN RSA PRIVATE KEY-----','-----END RSA PRIVATE KEY-----')
            copy_part_file(client_key,f_out,'-----BEGIN PRIVATE KEY-----','-----END PRIVATE KEY-----')
            jump_line=0
            f_out.write(line)

    timeStr = time.strftime('%Y-%m-%-d %H:%M:%S: ', time.localtime(time.time()))
    f_out.write('#'+timeStr)
    
    f_in.close()
    f_out.close()
    return True, client_conf

def cert_init():
    logger.info('...init server cert')
    if check_server_need() is not True: 
        try:
            clean_keys_dir()
            source_env()
            build_root_ca()   
            build_key_crt('server')
            build_key_crt('client')
            fast_cp_dh()
            #build_dh()
        except Exception,e:
	    logger.error(str(e))
            if hasattr(e, 'value'):
                return e.value
            else:
                return generalErrors[2]
    return True

def main():
    #print check_conf_file_need()
    generate_all()
    #generate_client_conf()
    
if __name__ == '__main__':
    main()

