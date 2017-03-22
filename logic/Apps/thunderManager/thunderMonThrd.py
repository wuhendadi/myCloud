import threading
import os
import time
import Tlog
import thunderSysUtils
import subprocess
import license

TAG = 'ThunderMonitorThread'
THUNDER_WORKSPACE_DIR_BIN_PORTAL = '/usr/local/etc/thunder/portal' 

OKAY = 'Ok'
FAILED = 'Failed'

class ThunderMonitorThread(threading.Thread):
    def __init__(self, interval, license_file, license_host, license_interface):
        threading.Thread.__init__(self)

        self.__stop_event = threading.Event()

        self.interval = interval

        self.tsu = thunderSysUtils.ThunderSysUtils()
        self.l = license.LicenseFile(license_file, license_host, license_interface)

    def start_thunder(self):
        Tlog.log_debug(TAG, "Starting thunder in thread and waiting here...")

        self.tsu.kill_all_thunder_processes()

        license = self.l.get_license()

        sub_p = subprocess.Popen([THUNDER_WORKSPACE_DIR_BIN_PORTAL, '-l' + license]).wait()

    def __check_thunder_runtime_sysinfo(self):
        sysinfo = self.tsu.get_sysinfo()

        try:
            if sysinfo[0] == 0:
                net_ok = True if sysinfo[1] == 1 else False
                if not net_ok:
                    Tlog.log_war(TAG, 'Check net ====>> %s'%(OKAY if net_ok else FAILED))

                license_ok = True if sysinfo[2] == 1 else False
                if net_ok and not license_ok:
                    self.l.delete()
                    Tlog.log_war(TAG, 'Check license =====>> %s'%(OKAY if license_ok else FAILED))

                bind_ok = True if sysinfo[3] == 1 else False
                if not bind_ok:
                    Tlog.log_war(TAG, 'Check bind result =====>> %s'%(OKAY if bind_ok else FAILED))

                disk_ok = True if sysinfo[5] == 1 else False
                if not disk_ok:
                    Tlog.log_war(TAG, 'Check disk =====>> %s'%(OKAY if disk_ok else FAILED))
                
                return net_ok and license_ok and bind_ok and disk_ok
            else:
                return False
        except IndexError:
            return False

    def run(self):
        Tlog.log_info(TAG, "Starting thunder monitor thread ...")
        self.start_thunder()

        while True:
            if self.__stop_event.wait(timeout=self.interval):
                self.__stop_event.clear()
                break

            if self.tsu.is_thunder_stopped():
                Tlog.log_war(TAG, "Thunder is stopped, restarting it")
                self.start_thunder()
                continue

            if not self.__check_thunder_runtime_sysinfo():
                Tlog.log_err(TAG, "Thunder sysinfo validate failed!")
            else:
                Tlog.log_debug(TAG, "Seems everything goes ok ...")

        else:
            Tlog.log_war(TAG, "Thunder monitor thread exited, bye~")

    def stop(self):
        Tlog.log_war(TAG, "Set stop flag as true...")

        self.__stop_event.set()

        self.join(5)

        self.tsu.kill_all_thunder_processes() 
