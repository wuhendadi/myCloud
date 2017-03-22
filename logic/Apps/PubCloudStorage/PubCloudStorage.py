import UtilFunc
import copy
import Queue
import baiducloud
import request
from baiducloud import errors
import json
import os
import os.path

logger = UtilFunc.getLogger()

SERVER_NAME = u'PubCloudStorage'
MAX_REQUESTS = 0  #infinite

CLOUD_BACKUP_WORKSPACE = '/data/popoCloudData/CloudBackup/baidupcs/'

class PubCloudStorage():
    def __init__(self):
        self.__cloud_dict = {}

        self.create_workspace()

        #for Baidu pcs
        self.__baidupcs_q = Queue.Queue(MAX_REQUESTS) 
        self.__cloud_dict.update(dict(baidu=self.__baidupcs_q))

        self.__BPMgrThrd = None

    def start(self):
        if self.__BPMgrThrd:
            self.__BPMgrThrd.stop()
        self.__BPMgrThrd = baiducloud.baiduPcsManagerThrd.BaiduPcsManagerThrd(self.__baidupcs_q)
        self.__BPMgrThrd.start()

    def handleHttpReq(self, method, **param):
        mParam = copy.deepcopy(param)

        try:
            req = request.Request(method, mParam)
            PublicCloud = param[u'name']
            q = self.__cloud_dict[PublicCloud]
            q.put(req)
            res = req.getResponse()
            return res
        except KeyError:
            res = dict(result=1, error_code=errors.UNSUPPORTED_CLOUD)
            return json.dumps(res)

    def stop(self):
        if self.__BPMgrThrd:
            self.__BPMgrThrd.stop()
            self.__BPMgrThrd.join()
            logger.debug(u'BPMgrThrd thread joined')
            self.__BPMgrThrd = None
        
    def create_workspace(self):
        if not os.path.exists(CLOUD_BACKUP_WORKSPACE):
            os.makedirs(CLOUD_BACKUP_WORKSPACE)