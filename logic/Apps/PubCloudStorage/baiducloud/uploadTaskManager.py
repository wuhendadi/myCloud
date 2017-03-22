import threading
import os
from os.path import join, getsize, isdir, isfile, splitext,split, exists
import Queue
from .. import request
import UtilFunc
import json
import errors
from .. import utils
import time
import backupDbOperation
import traceback

CANCEL_JOB_REQ = u'CancelBackupJob'
BACKUP_JOB_REQ = u'BackupToCloud'
logger = UtilFunc.getLogger()

class UploadTaskManager(threading.Thread):
    def __init__(self, upldMgrQ, upldAgntQ, pcs, upload_thread):
        threading.Thread.__init__(self)
        self.__upldMgrQ = upldMgrQ
        self.__upldAgntQ = upldAgntQ
        self.__pcs = pcs
        self.__upload_thread = upload_thread

    def createJobs(self, paths, req):
        msg = req.msg
        param = req.param
        parameter = {}
        failed_p = []
        success_p = []
        uuid_cache = {}

        for key in param:
            parameter.update({key:param[key]})

        for p in paths:
            #logger.debug(u'handing path %s' % p)
            if not exists(p):
                failed_p.append(dict(path=p,errCode=errors.FILE_NOT_EXISTS))
                continue
            else:
                dev_node, path_disk = utils.getDevNodeAndDiskRoot(p)
                if uuid_cache.get(dev_node, None):
                    disk_uuid = uuid_cache.get(dev_node)
                else:
                    disk_uuid = utils.getDiskUuidFromDevNd(dev_node)
                    uuid_cache.update(dict(dev_node=disk_uuid))

            res = backupDbOperation.get_backup_record_by_path(request.Request(None, dict(uuid=disk_uuid, path_disk=path_disk)))
            if res.get(u'error_code', 0):
                failed_p.append(dict(path=p,errCode=errors.DATABASE_ERROR))
                continue

            record = res.get(u'data')
            if not record:
                parameter.update(dict(path=p, uuid=disk_uuid, path_disk=path_disk))
                sub_req = request.Request(msg, parameter)
                request_id = sub_req.getId()
                backupDbOperation.insert_backup_record(sub_req)
                #logger.debug(u'Dispatching BackupToCloud %s to uploadAgent queue'%p)
                self.__upldAgntQ.put_nowait(sub_req)
            else:
                ctime = int(time.time())
                mesg = record.get(u'msg')
                request_id = record.get(u'request_id')
                status = record.get(u'status')
                pm = record.get(u'param')
                pm.update(dict(path=p))
                if status in [request.STATUS_PENDING, request.STATUS_PROCESSING]:
                    logger.debug(u'record is under processing.')
                    continue
                status = request.STATUS_PENDING
                backupDbOperation.update_backup_record(request.Request(None, dict(request_id=request_id, ctime=ctime, status=status, param=pm)))
                sub_req = request.Request(mesg, pm, request_id)
                #logger.debug(u'Dispatching ReBackupToCloud %s to uploadAgent queue'%p)
                self.__upldAgntQ.put_nowait(sub_req)
            success_p.append(dict(path=p, request_id=request_id))
        return dict(failed=failed_p, success=success_p)

    def handleRequest(self, req):
        msg = req.msg
        if msg == BACKUP_JOB_REQ:
            param = req.param
            paths = param.get(u'path')
            if paths:
                try:
                    jobs_d = self.createJobs(paths,req)
                    res = {u'result':0}
                    res.update(dict(data=jobs_d))
                except Queue.Full:
                    res = {u'result':1, u'error_code':errors.MAX_REQUESTS}
            else:
                logger.error(u'No path specified in backuptocloud request')
                res = {u'result':1,  u'error_code':errors.INVALID_PARAMS}
        elif msg == CANCEL_JOB_REQ:
            request_id = req.param.get(u'request_id')
            self.cancel_job(request_id)
            res = {u'result':0,u'data':''}
        else:
            res = dict(result=1, error_code=errors.UNSUPPORTED_METHODS)
        req.setResponseData(json.dumps(res))
        req.done()

    def cancel_job(self, request_id):
        """
        None means current job.
        """
        self.__upload_thread.cancel_current_upload(request_id)

    def run(self):
        backupDbOperation.handle_deprecated_shelve_data()
        backupDbOperation.paused_all_unfinished_records()
        while True:
            try :
                req = self.__upldMgrQ.get()
                msg = req.msg
                if msg == u'Quit':
                    logger.debug(u'UploadTaskManager receive a quit msg, leaving now')
                    break

                session, account = self.__pcs.get_session_info()
                if not account:
                    res = {u'result':1,u'error_code':errors.UNBIND}
                    req.setResponseData(json.dumps(res))
                    req.done()
                elif not session:
                    res = {u'result':1, u'error_code':errors.SESSION_EXPIRED}
                    req.setResponseData(json.dumps(res))
                    req.done()
                else:
                    self.handleRequest(req)
            except Queue.Full:
                res = {u'result':1, u'error_code':errors.MAX_REQUESTS}
                req.setResponseData(json.dumps(res))
                req.done()
            except Exception, e:
                logger.error(u'Get a fatal error: %s' % str(e))
                logger.error(traceback.format_exc())
        logger.debug(u'UploadTaskManager exist!')
