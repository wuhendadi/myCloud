#####################################################################
#Different with start_thunder.py, ThunderManager.py is another version
#of thunder, where it offers a thundermanager class, and it's methods
#to start/stop thunder, to get thunder interner sys info, and so on.
#
#####################################################################
import json
import Tlog
import os
import httpGet
import time
import UtilFunc

ERROR_LICENSE_STRING = "errorlicense"
LICENSE_LENGTH  =   42 
TAG = "LICENSE"

class LicenseFile:
    def __init__(self, filename, host, interface):
        self.filename = filename
        self.host = host
        self.interface = interface
        self.license = ERROR_LICENSE_STRING

    def __file_exist(self):
        ret = os.path.isfile(self.filename)
        return ret

    def __save(self):
        sf_hd = open(self.filename, 'w')
        sf_hd.write(self.license)
        sf_hd.close()

    def delete(self):
        if self.license_file_exist():
            os.remove(self.filename)
        else:
            pass

    def __read_from_file(self):
        try:
            file_handler = open(self.filename,'r')
            self.license = file_handler.read(LICENSE_LENGTH)
            file_handler.close()
        except IOError :
            self.license = ERROR_LICENSE_STRING
            Tlog.log_err(TAG, 'Error when read license file!')
            
            return False
        else :
            Tlog.log_debug(TAG, 'Read license:%s from file!'%self.license)
            return True

    def is_license_validate(self, ls):
        if ls == ERROR_LICENSE_STRING or len(ls) != LICENSE_LENGTH :
            return False
        else :
            return True

    def __get_from_internet(self):
        url = self.interface + '?serialNo=' + UtilFunc.getSN() + "&mac=" + UtilFunc.getMac()
        Tlog.log_debug(TAG, 'host:%s, method:%s, url:%s'%(self.host,'GET',url))

        lshttp = httpGet.HttpRequestGet(self.host, url)
        lsres = lshttp.get_response()
        try :
            js = json.loads(lsres[1])
        except ValueError :
            self.license = ERROR_LICENSE_STRING
            return False
        else :
            if lsres[0] == 'Ok' and js['result'] == 0 :
                self.license = js['license'].strip()
                return True
            else :
                self.license = ERROR_LICENSE_STRING
                return False

    def get_license(self):
        if self.__file_exist():
            if self.__read_from_file() and self.is_license_validate(self.license):
                return self.license
            else:
                self.delete()

        while not self.__get_from_internet() and  not self.is_license_validate(self.license):
            Tlog.log_debug(TAG, 'license string: %s'%self.license)
            Tlog.log_war(TAG, 'Retrying to get license from server after 5 seconds...')
            time.sleep(5)
        else:
            self.__save()

        return self.license
