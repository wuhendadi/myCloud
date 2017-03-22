import threading
import json
import os
from os.path import join
import UtilFunc
from .. import request
from uploadTaskManager import CANCEL_JOB_REQ
import errors
import backupDbOperation
from .. import utils
from accountManager import UNBINDED
import traceback

GET_BACKUP_RECORD       = u'GetBackupRecord'
QUERY_JOB_STATUS        = u'QueryJobStatus'
DELETE_BACKUP_RECORDS   = u'DeleteBackupRecords'
GET_ALL_BACKUP_RECORDS  = u'GetAllBackupRecords'

logger = UtilFunc.getLogger()

class GeneralTaskManager(threading.Thread):
    def __init__(self, req_q, upldMgr_q, pcs):
        threading.Thread.__init__(self)
        self.__reqQ = req_q
        self.__upldMgrQ = upldMgr_q
        self.__pcs = pcs

    def getBackupRecord(self, req):
        param = req.param
        req_id = param.get(u'request_id','')

        try:
            start = int(param.get(u'start', u'0'))
            count = int(param.get(u'count', u'-1'))
        except ValueError:
            res = {u'result':1, u'error_code':errors.INVALID_PARAMS}
            return res

        relevant_path = param.get(u'relevant_path','')
        if req_id == '' or not relevant_path.startswith(os.sep):
            res = {u'result':1, u'error_code':errors.INVALID_PARAMS}
            return res

        relevant_path = relevant_path.strip(os.sep)
        res = backupDbOperation.get_backup_record_by_req_id(req)
        if not res.get(u'error_code', 0):
            record = res.get(u'data')
            uuid = record.get(u'uuid')
            path_disk = record.get(u'path_disk')
            db_access_p = join(path_disk, relevant_path).rstrip(os.sep) + os.sep
            sub_req = request.Request(None, dict(uuid=uuid, path=db_access_p, name=u'baidu', request_id=req_id, start=start, count=count))
            res = backupDbOperation.query_backup_record_contents(sub_req)

        logger.debug(u'Query backup record result:%s'%res)
        return res

    def getAllBackupRecords(self, req):
        logger.debug(u'Get all the backup records...')
        param = req.param
        try:
            start = int(param.get(u'start', u'0'))
            count = int(param.get(u'count', u'-1'))
        except ValueError:
            res = {u'result':1, u'error_code':errors.INVALID_PARAMS}
            return res

        path_cache = {}
        res = backupDbOperation.get_backup_records(req)
        if res.get(u'error_code', 0):
            return {u'result':1, u'error_code':errors.DATABASE_ERROR}

        records = res.get(u'data', [])
        for record in records:
            uuid = record.pop(u'uuid')
            path_disk = record.pop(u'path_disk')
            if path_cache.get(uuid, None):
                local_path_root = path_cache.get(uuid, None)
            else:
                local_path_root = utils.getPopoboxPathFromUuid(uuid)
                path_cache.update({uuid:local_path_root})
            if not local_path_root:
                local_path = ''
            else:
                local_path = join(local_path_root, path_disk.strip(os.sep))
            record.update(dict(local_path=local_path))
        return {u'result':0, u'data':records}

    def deleteBackupRecords(self, req):
        param = req.param
        request_ids = param.get(u'request_ids')
        records = []
        failed = []
        success = []

        if not request_ids or not isinstance(request_ids,list):
            logger.debug(u'request_ids is empty or not a valid list')
            return {u'result':1, u'error_code':errors.INVALID_PARAMS}

        for req_id in request_ids:
            res = backupDbOperation.get_backup_record_by_req_id(request.Request(None, dict(request_id=req_id)))
            if res.get(u'error_code', 0):
                failed.append(dict(request_id=req_id, errCode=res.get(u'error_code')))
                continue

            record = res.get(u'data')
            if not record:
                failed.append(dict(request_id=req_id, errCode=errors.JOB_NOT_EXISTS))
                continue

            uuid = record.get(u'uuid')
            status = record.get(u'status')
            if status in [request.STATUS_PROCESSING]:
                logger.debug(u'delete record when processing, need to cancel uploading job')
                cancel_req = request.Request(CANCEL_JOB_REQ, dict(request_id=req_id))
                self.__upldMgrQ.put(cancel_req)
                cancel_req.getResponse()
            records.append(dict(request_id=req_id, uuid=uuid))
            success.append(req_id)

        if records:
            backupDbOperation.delete_backup_records(request.Request(None, dict(records=records)))

        data = dict(success=success,failed=failed)
        res = {u'result':0, u'data':data}
        return res

    def deleteRecords4Unbind(self):
        logger.debug(u'Delete all backup records')
        cancel_req = request.Request(CANCEL_JOB_REQ, dict(request_id=None))
        self.__upldMgrQ.put(cancel_req)
        cancel_req.getResponse()
        res = backupDbOperation.delete_all_backup_records()
        res = {u'result':0, u'data':''}
        return res

    def queryJobStatus(self, req):
        param = req.param
        req_id = param.get(u'request_id','')

        if not req_id:
            return {u'result':1, u'error_code':errors.INVALID_PARAMS}

        logger.debug(u'Query request:%s'%req_id)
        res = backupDbOperation.get_backup_record_by_req_id(request.Request(None, dict(request_id=req_id)))
        if not res.get(u'error_code', 0):
            record = res.get(u'data')
            status=record.get(u'status', request.STATUS_FAILED)
            error_code = record.get(u'error_code', 0)
            res = {u'result':0, u'data':dict(status=status, errCode=error_code)}
        logger.debug(u'Query result:%s'%res)
        return res

    def run(self):
        logger.debug(u'start GeneralTaskManager')
        while True:
            try:
                req = self.__reqQ.get()
                if req.msg == u'Quit':
                    break
                msg = req.msg
                logger.debug(u'Receiving a message %s, handle it!'%msg)
                session, account = self.__pcs.get_session_info()
                if not account:
                    res = {u'result':1,u'error_code':errors.UNBIND}
                elif not session:
                    res = {u'result':1, u'error_code':errors.SESSION_EXPIRED}
                else:
                    if req.msg == GET_BACKUP_RECORD:
                        res = self.getBackupRecord(req)
                    elif req.msg == QUERY_JOB_STATUS:
                        res = self.queryJobStatus(req)
                    elif req.msg == GET_ALL_BACKUP_RECORDS:
                        res = self.getAllBackupRecords(req)
                    elif req.msg == DELETE_BACKUP_RECORDS:
                        res = self.deleteBackupRecords(req)
                    elif msg == UNBINDED:
                        res = self.deleteRecords4Unbind()
                req.setResponseData(json.dumps(res))
                req.done()
            except Exception,e:
                logger.error(u'GeneralTaskManager get one fatal error :%s' % str(e))
                logger.error(traceback.format_exc())
