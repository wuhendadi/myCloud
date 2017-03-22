# -*- coding: utf-8 -*-
#author:ZJW

import os
import sys
import time
import platform
import UtilFunc
import ProfileFunc
import Log
from PopoConfig import VersionInfo, Hardware

def showSystemInfo():
    Log.info("System Info")
    Log.info("-->File encoding      : " + repr(sys.getfilesystemencoding()))
    Log.info("-->Architecture       : " + repr(platform.architecture()))
    Log.info("-->Info               : " + repr(platform.uname()))
    Log.info("-->Default encoding   : " + repr(sys.getdefaultencoding()))
    Log.info("-->Local IP           : " + repr(UtilFunc.getLocalIp()))
    Log.info("-->Executable Argument: " + repr(sys.argv))
    Log.info("-->PopoCloud Version  : " + repr(VersionInfo))
    Log.info("-->System Version     : " + repr(UtilFunc.getSystemVersion()))
    Log.info("-->Serialno           : " + repr(UtilFunc.getSN()))
    
def syncSystemTime(date=None):
    if date and time.strftime("%Y", time.localtime(time.time())) == "1970":
        Log.info("SyncSystemTime from Hub-Service!")
        time_str = ".".join(date.split())
        os.system("date -s 20%s"%time_str)
        
def setOsEnv(colstr):
    try:
        if not UtilFunc.isLinuxSystem():
            return
        from Sitelib import libandroidmod
        address = libandroidmod.property_gets(colstr)
        if address:
            os.environ[colstr] = address
    except Exception,e:
        Log.exception('setOsEnv Exception! Reason[%s]'%e)

def getStorageName(path):
    num = 1
    if UtilFunc.isLinuxSystem():
        path = UtilFunc.getDiskPath(path)
        if path == '/mnt/popoCloud': return 'Storage1'
        key = 'Storage'
    else:
        key = 'Folder'
    
    for disk in ProfileFunc.GetBoxDisks(False):
        if path == disk: 
            return key+str(num)
        num += 1
    return None
        
def getDiskInfo(path):
    sid, fs, name = '', '', getStorageName(path)
    if UtilFunc.isLinuxSystem(): 
        from Sitelib import libandroidmod
        diskinfo = libandroidmod.execute_shell("busybox df '" + str(path) + "'").split('\n')
        if diskinfo:
            mount_path = diskinfo[1].split()[0]
            disklist = libandroidmod.execute_shell('blkid -s LABEL -s UUID -d')
            start = disklist.find(mount_path + ':')
            if start != -1:
                strline = disklist[start:(start + disklist[start:].find('\n'))].strip()
                id_index = strline.find('UUID=')
                sid = strline[id_index+6:-1]
                try:
                    label_index = strline.find('LABEL=')
                    if int(label_index) > 0:
                        name = name + '(' + strline[label_index+7:id_index-2].decode('gbk') + ')'
                    print name
                except Exception, e:
                    Log.exception("GetLabel Failed! Reason[%s]"%e)
                      
            mountinfo = libandroidmod.execute_shell('mount').split('\n')
            for line in mountinfo:
                if mount_path in line.split():
                    fs = line.split()[2]
                    
    elif UtilFunc.isWindowsSystem():
        sid = UtilFunc.getDiskPath(path)[:1]
    
    elif UtilFunc.isDarwinSystem():
        sid = 'HD'
                      
    return sid,fs,name
        
def umountDisks(diskId=None):
    if Hardware == "1.0":
        for subFile in os.listdir('/mnt/disks'):
            if "sd" in file:
                path = os.path.join('/mnt/disks', subFile)
                os.system('umount -v %s'%path)
    else:
        if UtilFunc.versionCompare(UtilFunc.getSystemVersion(), '1.5.4'):
            os.system('vdc volume pb-unmount all')
            return
            
        list_files = os.listdir('/popobox')
        from Sitelib import libandroidmod
        for oneFile in list_files:
            if "disk" in oneFile: disk = os.path.join('/popobox', oneFile)
            for part in os.listdir(disk):
                if "part" in part:
                    try:
                        path = libandroidmod.execute_shell('ls -l %s'%'/mnt/' + oneFile + '/' + part)
                        if path: 
                            path = path.split()[7]
                            os.system('vdc volume unmount %s force'%path)
                    except Exception,e:
                        Log.exception("Umount Disk Failed! Reason[%s]"%e)
                        continue
                        
#            os.system('rm -r %s'%disk)
#            os.system('rm -r %s'%disk.replace('/popobox/','/mnt/'))

def resetDHCP():
    if Hardware == "1.0":
        pipe = os.popen("ps -o pid,comm")
        pids = pipe.readlines()
        pipe.close()
        for pid in pids:
            if "udhcpc" in pid:
                pid_no = pid.split()[0]
                os.system("kill -9 %d"%int(pid_no))
                Log.info("Kill Udhcp process! Please Wait!")
        os.system("udhcpc -i eth0")
        Log.info("ReStart Udhcp process Successful!")
    time.sleep(10)

def ledFlash(status, frame=None):
    if UtilFunc.isWindowsSystem():
        return
        #frame.ChangeRelayStatus(status)
    elif Hardware == "1.0":
        if status == 0: #红灭/绿中速闪烁
            os.system('left_led_off')
            os.system('right_led_flash')
            os.system('flash_mid')
        elif status == 1: #红中速闪烁 /绿灭
            os.system('right_led_off')
            os.system('left_led_flash')
            os.system('flash_mid')
        elif status == 2: #红灭/绿亮
            os.system('left_led_off')
            os.system('right_led_on')
        elif status == 3: #红亮/绿灭
            os.system('left_led_on')
            os.system('right_led_off')
    else:
        if status == 0:#红/蓝交替快闪
            os.system("ktled 10")
        elif status == 1:#红/蓝交替慢闪
            os.system("ktled 1")
        elif status == 2:#蓝灯常亮
            if ProfileFunc.isAllDiskScaned():
                os.system("ktled b")
            else:
                os.system("ktled 1")
        elif status == 3:#红灯常亮
            if ProfileFunc.isAllDiskScaned():
                os.system("ktled r")
            else:
                os.system("ktled 1")
                
                