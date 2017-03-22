#####################################################################
#System interface for thunder, remote call, sysinfo, kill process, 
#and so on
#####################################################################
import os
import sys
import json
import httpGet
import Tlog

TAG = "ThunderSysUtils"
OKAY = 'Ok'
FAILED = 'Failed' 

class ThunderSysUtils:
    def __init__(self):
        pass

    def __kill_process_by_name(self, process):
        command = 'busybox killall -q ' + process
        ret = os.system(command)
        ret = ret >> 8
        Tlog.log_debug(TAG, 'Try to kill process: %s, ret: %d'%(process, ret))

        return ret

    def kill_all_thunder_processes(self):
        self.__kill_process_by_name('portal')
        self.__kill_process_by_name('ETMDaemon')
        self.__kill_process_by_name('EmbedThunderManager')

    def is_thunder_stopped(self):
        ret = 0

        #ret |= os.system('pgrep portal')
        ret |= os.system('pgrep ETMDaemon > /dev/null')
        ret |= os.system('pgrep EmbedThunderManager > /dev/null ')

        return True if (ret >> 8) != 0 else False

    def call_remote_interface(self,url):
        '''
            returns: tuple
                'Ok', res_string         : if http request returns normally
                'Failed', ''             : if http request failed
        '''
        hrg =httpGet.HttpRequestGet('127.0.0.1:9000', url)
        res = hrg.get_response()

        if res[0] != OKAY:
            Tlog.log_err(TAG, 'Error happens when call thunder remote interface: %s'%res[1])
            return FAILED, ''
        else:
            return OKAY, res[1]

    def get_sysinfo(self):
        '''
            This method returns inner sys info of thunder

            returns:
                json formatted data : if http request returns normally
                [None string]       : if http request failed
        '''
        res = self.call_remote_interface('/getsysinfo')
        try:
            if res[0] == OKAY:
                sysinfo = json.loads(res[1])
            else:
                sysinfo = ''
        except ValueError :
            sysinfo = ''

        Tlog.log_debug(TAG, 'Thunder sysinfo:%s'%sysinfo)
        return sysinfo

    def unbind_thunder(self):
        Tlog.log_info(TAG, 'Unbinding thunder...')
        res_string = self.call_remote_interface('/unbind')

        if res_string[0] == OKAY:
            res_json = json.loads(res_string[1])

            ret =  OKAY if res_json[0] == 0 else FAILED
        else:
            ret = FAILED

        Tlog.log_info(TAG, 'Unbinding thunder, result: %s'%ret)
        return ret

    def get_active_key(self):
        '''
            returns: tuple
                'Ok', 'active key'  :
                    active key would be none if thunder already get binded.
                'Failed', ''        :
                    case 1: thunder not get started yet
                    case 2: error happens
        '''
        res = self.get_sysinfo()

        try:
            ret = OKAY, res[4]
        except IndexError:
            ret = FAILED, ''

        Tlog.log_debug(TAG, 'get_active_key, result:%s, active_key:%s'%ret)
        return ret
