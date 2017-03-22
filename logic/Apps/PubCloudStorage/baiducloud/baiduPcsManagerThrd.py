import threading
import Queue
import uploadTaskManager
from uploadTaskManager import BACKUP_JOB_REQ,CANCEL_JOB_REQ
import generalTaskManager
from generalTaskManager import GET_BACKUP_RECORD, QUERY_JOB_STATUS, DELETE_BACKUP_RECORDS, GET_ALL_BACKUP_RECORDS
import accountManager
from accountManager import BIND_CLOUD_ACCOUNT, UNBIND_CLOUD_ACCOUNT, GET_CLOUD_ACCOUT, GET_TOKEN
from .. import request
import popoCloudPCS
import UtilFunc
import json
import errors
import os
import os.path
import uploadAgentThrd

logger = UtilFunc.getLogger()

Queue_Max_Reqs = 100
GENERAL_REQ_LIST =[GET_BACKUP_RECORD, QUERY_JOB_STATUS, DELETE_BACKUP_RECORDS, GET_ALL_BACKUP_RECORDS]
ACCOUNT_REQ_LIST = [BIND_CLOUD_ACCOUNT, UNBIND_CLOUD_ACCOUNT, GET_CLOUD_ACCOUT, GET_TOKEN]
UPLOADMGR_REQ_LIST = [BACKUP_JOB_REQ, CANCEL_JOB_REQ]

class BaiduPcsManagerThrd(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)

        self.__generalQ = Queue.Queue(Queue_Max_Reqs)
        self.__uploadMgrQ = Queue.Queue(Queue_Max_Reqs)
        self.__accMgrQ = Queue.Queue(Queue_Max_Reqs)
        self.__uploadAgentQ = Queue.Queue()  #infinite size Queue

        self.__event = threading.Event()
        self.__req_queue = queue
        self.__pcs = popoCloudPCS.PopoCloudPCS(self.__accMgrQ)

        self.__accMgr = accountManager.AccountManager(self.__accMgrQ, self.__generalQ, self.__pcs)
        self.__UploadAgentThrd = uploadAgentThrd.UploadAgentThrd(self.__uploadAgentQ, self.__pcs)
        self.__ulMgrThrd = uploadTaskManager.UploadTaskManager(self.__uploadMgrQ, self.__uploadAgentQ, self.__pcs, self.__UploadAgentThrd)
        self.__gnrlMgrThrd = generalTaskManager.GeneralTaskManager(self.__generalQ, self.__uploadMgrQ, self.__pcs)

    def dispatchReq(self,req):
        msg = req.msg
        param = req.param

        try:
            if msg in GENERAL_REQ_LIST:
                logger.debug(u'Dispatching message %s to general task queue'%msg)
                self.__generalQ.put_nowait(req)
            elif msg in ACCOUNT_REQ_LIST:
                logger.debug(u'Dispatching message %s to account task queue'%msg)
                self.__accMgrQ.put_nowait(req)
            elif msg in UPLOADMGR_REQ_LIST:
                logger.debug(u'Dispatching message %s to upload task queue'%msg)
                self.__uploadMgrQ.put_nowait(req)
            else:
                logger.warn(u'Unsupported message: %s, ignored!'%msg)
                res = {u'result':1,  u'error_code':errors.UNSUPPORTED_METHODS}
                req.setResponseData(json.dumps(res))
                req.done()
        except Queue.Full:
            res = {u'result':1, u'error_code':errors.MAX_REQUESTS}
            req.setResponseData(json.dumps(res))
            req.done()

    def run(self):
        self.__accMgr.start()
        self.__gnrlMgrThrd.start()
        self.__ulMgrThrd.start()
        self.__UploadAgentThrd.start()
        while True:
            if self.__event.wait(timeout=0):
                break
            else:
                req = self.__req_queue.get()
                logger.debug(u'BaiduPcsManager receive a request, try to dispatch it.')
                self.dispatchReq(req)
        logger.debug(u'Sending quit message to sub threads!')
        req = request.Request(u'Quit', None)
        for q in [self.__generalQ, self.__accMgrQ, self.__uploadMgrQ, self.__uploadAgentQ]:
            q.put(req)
        self.__accMgr.join()
        logger.debug(u'Accoutmanager thread joined')
        self.__gnrlMgrThrd.join()
        logger.debug(u'General task thread joined')
        self.__ulMgrThrd.join()
        logger.debug(u'upload manager thread joined')
        self.__UploadAgentThrd.join()
        logger.debug(u'upload agent thread joined')

    def stop(self):
        logger.warn(u'Receiving quit event!, baiduPcsManagerThrd is going to end itself!')
        self.__event.set()
        quit_req = request.Request(u'Quit',None)
        self.__req_queue.put(quit_req)
