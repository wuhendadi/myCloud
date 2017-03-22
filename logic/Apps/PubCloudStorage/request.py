import copy
import threading
import uuid
from baiducloud import errors
import json

##Request status
STATUS_PAUSED = u'paused'
STATUS_PENDING = u'pending'
STATUS_PROCESSING = u'processing'
STATUS_FAILED = u'failed'
STATUS_SUCCESS = u'success'

class Request():
    def __init__(self, message, param, request_id=None):
        self.msg = message
        self.param = copy.deepcopy(param) #deepcopy()
        self.__event = threading.Event()
        self.__data = {}
        self.__job_file = ''
        self.status = STATUS_PENDING #default is pending
        if request_id:
            self.__id = request_id
        else:
            self.__id = self.__generateReqId()
        self.__cancel_upload_event = threading.Event()

    def getId(self):
        return self.__id

    def setResponseData(self, res):
        self.__data = res

    def setJobFile(self, path):
        self.__job_file = path

    def getJobFile(self):
        return self.__job_file

    def getResponse(self):
        if self.__event.wait(timeout=120):
            return self.__data
        else:
            data = {u'result':1,u'error_code':errors.TIMEOUT}
            return json.dumps(data)

    def done(self):
        self.__event.set()

    def __generateReqId(self):
        #generate id from uuid module, based on hostname and time
        return str(uuid.uuid1())

    def cancel_upload(self, request_id):
        """
        if request_id is None, cancel current upload request message.
        """
        if not request_id or self.getId() == request_id:
            self.__cancel_upload_event.set()

    def is_cancel_upload(self):
        return self.__cancel_upload_event.is_set()
