import sys
import httplib
import Tlog

TAG = 'HttpRequestGet'

class HttpRequestGet:
    def __init__(self, host, url):
        self.host = host
        self.url = url

    def get_response(self): 
        try :
            Tlog.log_debug(TAG, 'Try http \'Get\' method, host: %s, url: %s'%(self.host, self.url))
            connection = httplib.HTTPConnection(self.host)
            connection.request('GET', self.url)
            res = connection.getresponse()
            data = res.read()

            if res.status == 200:
                ret = ('Ok', data)
                Tlog.log_debug(TAG, 'Data:%s'%data)
            else:
                ret = ('Failed', 'Error code:%d'%res.status)
                Tlog.log_err(TAG, 'Failed!')
        except Exception :
            info = sys.exc_info()
            ret = ('Failed', '%s:%s'%(info[0], info[1]))
            Tlog.log_err(TAG, 'Exception! %s:%s'%(info[0], info[1]))
        else :
            connection.close()

        return ret
