#####################################################################
#Different with start_thunder.py, ThunderManager.py is another version
#of thunder, where it offers a thundermanager class, and it's methods
#to start/stop thunder, and so on.
#####################################################################
import os
import sys
import subprocess
import license
import Tlog
import thunderMonThrd
import thunderSysUtils

TAG = 'ThunderManager'
SERVER_NAME = None

THUNDER_WORKSPACE_DIR_TMP = '/tmp'
THUNDER_WORKSPACE_DIR_USR = '/usr/local/etc'
THUNDER_WORKSPACE_DIR_BIN = '/usr/local/etc/thunder'
THUNDER_WORKSPACE_DIR_BIN_PORTAL = '/usr/local/etc/thunder/portal'
THUNDER_SOURCE_DIR_BIN = '/system/bin/thunder/'
#THUNDER_SOURCE_DIR_TMP = '/system/bin/thunder/tmp'
THUNDER_SOURCE_DIR_TMP = '/data/popoCloudData/thunderTmp'

THUNDER_LICENSE_FILE_PATH = '/system/etc/license.dat'
THUNDER_HOST_NAME =  'my.paopaoyun.com'
THUNDER_LICENSE_INTERFACE = '/thunder/licenses'

class thunderManager():
    def __init__(self, filename = THUNDER_LICENSE_FILE_PATH, \
                host = THUNDER_HOST_NAME, \
                interface = THUNDER_LICENSE_INTERFACE,\
                thunder_source_bin = THUNDER_SOURCE_DIR_BIN, \
                thunder_source_tmp= THUNDER_SOURCE_DIR_TMP, \
                mode = "user" ):
        self.license = license.ERROR_LICENSE_STRING
        self.host = host
        self.interface = interface
        self.filename = filename
        self.thunder_source_tmp = thunder_source_tmp
        self.thunder_source_bin = thunder_source_bin

        self.tmt =None
        self.tsu = thunderSysUtils.ThunderSysUtils()

        self.__init_workspace()
        self.__init_check_bin_files()

        Tlog.set_mode(mode)

    def __init_workspace(self):
        if not os.path.exists(THUNDER_WORKSPACE_DIR_USR):
            os.makedirs(THUNDER_WORKSPACE_DIR_USR)

        if not os.path.exists(THUNDER_SOURCE_DIR_TMP):
            os.makedirs(THUNDER_SOURCE_DIR_TMP)

        if os.path.islink(THUNDER_WORKSPACE_DIR_BIN):
            os.unlink(THUNDER_WORKSPACE_DIR_BIN)
        os.symlink(self.thunder_source_bin, THUNDER_WORKSPACE_DIR_BIN)

        if os.path.islink(THUNDER_WORKSPACE_DIR_TMP):
            os.unlink(THUNDER_WORKSPACE_DIR_TMP)
        os.symlink(self.thunder_source_tmp, THUNDER_WORKSPACE_DIR_TMP)

    def __init_check_bin_files(self):
        if not os.access(THUNDER_WORKSPACE_DIR_BIN_PORTAL, os.X_OK):
            Tlog.log_debug(TAG, 'Add executable permission to portal')

            os.chmod(THUNDER_WORKSPACE_DIR_BIN_PORTAL, \
                stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

        if not os.access(THUNDER_WORKSPACE_DIR_BIN + '/lib/ETMDaemon', os.X_OK):
            Tlog.log_debug(TAG, 'Add executable permission to ETMDaemon')

            os.chmod(THUNDER_WORKSPACE_DIR_BIN + '/lib/ETMDaemon', \
                stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

        if not os.access(THUNDER_WORKSPACE_DIR_BIN + '/lib/EmbedThunderManager', os.X_OK):
            Tlog.log_debug(TAG, 'Add executable permission to EmbedThunderManager')

            os.chmod(THUNDER_WORKSPACE_DIR_BIN + '/lib/EmbedThunderManager',\
                 stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

    def __log_start(self):
        Tlog.log_info(TAG,'Starting thunder...')
 
    def __log_stop(self, is_thunder_stopped):
        if not is_thunder_stopped:
            Tlog.log_War(TAG, "Thunder processes are not exitst really, please check the log!")

        Tlog.log_war(TAG,'Thunder stopped!')

    def start(self):
        self.__log_start()

        # stop the previous threads if exist
        self.stop()

        self.tmt = thunderMonThrd.ThunderMonitorThread(30, self.filename,\
                        self.host, self.interface )

        self.tmt.setDaemon(False) 
        self.tmt.start()

    def restart(self):
        self.start()

    def stop(self):
        if self.tmt == None: 
            return

        if not self.tmt.isAlive():
            return

        Tlog.log_info(TAG, 'Stopping thunder...')

        self.tmt.stop()

        if self.tsu.is_thunder_stopped():
            self.__log_stop(True)
        else:
            self.__log_stop(False)

    def unbind(self):
        return self.tsu.unbind_thunder()

    def active_key(self):
        return self.tsu.get_active_key()
    
    def clean(self):
        return
