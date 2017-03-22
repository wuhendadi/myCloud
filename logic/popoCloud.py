# -*- coding: utf-8 -*-
import sys
import time
import os
import singleton
import UtilFunc
import PopoConfig
import ProfileFunc
import StartFunc
import popoUpdate
import Command
import Log
import urllib2
import thread

from CSTunnel import HubTunnel
from ScanFolderMoniter import ScanFolderMoniter

def initConsoleLog():
    #Create console log for popoCloud.pyc/popocloud.exe
    if UtilFunc.we_are_frozen() or os.path.basename(sys.argv[0]) == "popoCloud.pyc":
        consoleFile = Log.getLogDataPath() + "/popoCloud.console.log"
        sys.stdout = open(consoleFile, 'w')
        sys.stderr = sys.stdout
        UtilFunc.changeMod(consoleFile, 644)

def downloadGlobalConfig():
    if UtilFunc.isPCMode():
        return
    fp = None
    try:
        url = PopoConfig.ConfigUrl + UtilFunc.getSN()
        r = urllib2.urlopen(url)
        data = r.read()
        configPath = os.path.abspath(os.path.dirname(PopoConfig.Config_path))
        if not os.path.exists(configPath):
            os.makedirs(configPath)
        fp = open(PopoConfig.Config_path, "wb")
        fp.write(data)
    except Exception, e:
        Log.error("Update config Failed! Reason: %s"%e)
    finally:
        if fp: fp.close()

class Application():

    def __init__(self):
        self.services                = {}
        self.diskState               = {}
        self.diskInfo                = {}
        self.status                  = None
        self.hubTunnel               = HubTunnel()
        self.scanFolderMoniter       = ScanFolderMoniter(self)
        ProfileFunc._fileService     = self

    def pcServerStart(self):
        if UtilFunc.isWindowsSystem():
            import _winreg
            try:
                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PopoCloud")
                value,type = _winreg.QueryValueEx(key,'DisplayVersion')
    
                if value != PopoConfig.VersionInfo:
                    _winreg.CloseKey(key)
    
                    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,"Software\Microsoft\Windows\CurrentVersion\Uninstall\PopoCloud",0,_winreg.KEY_WRITE)
                    _winreg.SetValueEx(key,'DisplayVersion',0,_winreg.REG_SZ,PopoConfig.VersionInfo)
                    _winreg.CloseKey(key)
                else:
                    _winreg.CloseKey(key)
            except:
                Log.debug("DisplayVersion doesn't exit...")

        from interface import Frame
        Frame.runMainForm(None)

    def start(self):
        Command.ledFlash(0, None)
        if len(sys.argv) >=2 and sys.argv[1] == 'update':
            path = sys.argv[2]
            Frame.runMainForm(True)
        self.lock = singleton.SingleInstance(os.path.join(UtilFunc.getLockDataPath(), 'popoCloudApp.lock'))
        initConsoleLog()
        thread.start_new_thread(downloadGlobalConfig, ())
        Command.showSystemInfo()
#         if UtilFunc.isPCMode():
#             self.pcServerStart()
#         else:
#             Log.info("PopoCloud Service Action!")
#             StartFunc.action(self)
        StartFunc.action(self)
        while True:
            cur_time = time.localtime()
            offset = (24 - cur_time.tm_hour) * 3600
            for service in self.services.values():
                if hasattr(service,'clean'):
                    service.clean()
            Log.clean()
            time.sleep(offset)

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    Application().start()

