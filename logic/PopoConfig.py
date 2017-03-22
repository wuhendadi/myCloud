# -*- coding: utf-8 -*-
import os
import json
import platform
import ConfigParser

def getValue(option, value, pro='profile'):
    global cf
    try:
        return cf.get(pro, option)
    except:
        return value

def setValue(option, value, pro='profile'):
    global cf
    try:
        cf.set(pro, option, value)
        cf.write(open(CONFIGPATH,'w+'))
    except:
        return False
    return True

CONFIGPATH = os.path.dirname(os.path.abspath(__file__)) + "/config.conf"
systemInfo = platform.uname()
if 'Windows' in systemInfo:
    PlatformInfo = "Window_Desktop"
    Hardware = 'pc'
elif 'Linux' in systemInfo:
    if 'arm' in systemInfo[4]:
        PlatformInfo = "Box"
        if 'armv5tejl' in systemInfo:
            Hardware = "1.0"
        else:
            Hardware = "1.5"
    else:
        PlatformInfo = 'Linux'
        Hardware = 'pc'
elif 'Darwin' in systemInfo:
    PlatformInfo = "Mac_OS"
    Hardware = 'apple'
    CONFIGPATH = os.getcwd() + "/config.conf"
    
cf = ConfigParser.ConfigParser()
if os.path.exists(CONFIGPATH):
    cf.read(CONFIGPATH)

ServerHost        = getValue('serverhost', "cs-test.paopaoyun.com", pro='host&port')
ServerPort        = int(getValue('serverport', 80, pro='host&port'))
UpgradeHost       = getValue('upgradehost', "cs-test.paopaoyun.com", pro='host&port')
UpgradePort       = int(getValue('upgradeport', 9005, pro='host&port'))
AuthHost          = getValue('authhost', 'auth-test.paopaoyun.com', pro='host&port')
AuthPort          = int(getValue('authport', 8080, pro='host&port'))
VersionInfo       = getValue('versioninfo', "3.0.0", pro='version')
SESSION_TIMEOUT   = int(getValue('sessiontime', 15)) * 60
ISRELAY           = getValue('isrelay', True)
ViaEcs            = getValue('viaecs', True)
LogLevel          = int(getValue('loglevel', 3))
BoardSys          = getValue('board', 'linux')
MntName           = getValue('mntname', 'mnt')
UsbRoot           = getValue('usbroot', 'uhost')
CreateThumbNail   = getValue('thumbnail', True)
ScanFolder        = getValue('scanfolder', True)

try:
    UpnpPort = json.loads(getValue('upnpport', '{}', pro='host&port'))
except Exception,e:
    UpnpPort = {}

Popocloud_path = getValue('PopocloudPath', "/system/popocloud", pro='paths')
ConfigUrl = "http://servers.minisocials.com/servers/config?sn="

upnp_port   = 34562
mount_time  = 60
MinSpace    = 10*1024
BigImage    = 10*1024*1024
MaxLength   = 5100
MinImage    = 60*1024
MaxWidth    = 1024
MaxHeight   = 1024
MinWidth    = 170
MinHeight   = 170

Activation_path = "/popoCloudData/license.lock"
System_version  = "/system/software_ver/sys_version"
Key_value       = "13ThIs_Is_tHe_bouNdaRY_$"
Mode_value      = "^!^*$^**"
BT_wait         = 10*60

if Hardware == "1.0":
    Lock_path = "/var/lock"
    Log_path  = "/var/log/popoCloud"
    Upl_path  = "/var/log"
    App_path  = "/root"
    Sn_path   = "/sys/kernel/serial_number/sn"
else:
    Lock_path = "/popoCloudData/lock"
    Log_path  = "/popoCloudData"
    Upl_path  = "/popoCloudData/lock"
    App_path  = "/popoCloudData"
    Sn_path   = "/system/popocloud/sn"
    Config_path = "/mnt/sdcard/Elastos/config"

filters = {"picture"  : getValue('picture', '*.ai;*.bmp;*.bw;*.col;*.dwg;*.dxf;*.emf;*.gif;*.ico;*.jpg;*.jpeg;*.png;*.pcd;*.pcx;*.pic;*.psd;*.rel;*.tga;*.tiff;*.lzw;*.yuv;*.wmf;*.cr2', pro = 'filetypes'),
           "video"    : getValue('video', '*.mp4;*.m4v;*.mkv;*.xvid;*.wmv;*.rm;*.rmvb;*.vob;*.dat;*.vcd;*.dvd;*.svcd;*.asf;*.mov;*.qt;*.mpeg;*.3gp;*.divx;*.mpg;*.ts;*.navi;*.avi;*.flv;*.swf;*.fla;*.f4v', pro = 'filetypes'),
           "music"    : getValue('music', '*.ape;*.mp3;*.aac;*.wma;*.amr;*.flac;*.dsd;*.wav;*.ogg;*.pcm;*.vqf;*.cda;*.mid;*.awb;*.m4a;*.rtx;*.otc;*.imy;*.ota', pro = 'filetypes'),
           "app"      : getValue('app', '*.apk;*.eco;*.ecx;*.exe;*.ipo;*.ipa;*.iso', pro = 'filetypes'),
           "doc"      : getValue('doc', '*.doc;*.docx;*.ppt;*.txt;*.pdf;*.xls;*.txt;*.rar;*.zip;*.tmp;*.pptx;*.mdf;*.jnt;*.xml;*.wps;*.xlt;*.odt;*.ott;*.ods;*.cvs', pro = 'filetypes'),
           }