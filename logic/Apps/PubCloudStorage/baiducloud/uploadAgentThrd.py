import threading
import os
from os.path import join, getsize, isdir, isfile, splitext,split, exists
import UtilFunc
from .. import request
from .. import utils
import errors
import time
import backupDbOperation
import traceback

logger = UtilFunc.getLogger()

class CancelUploadError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class UploadAgentThrd(threading.Thread):
    def __init__(self, reqQ, pcs):
        threading.Thread.__init__(self)
        self.__reqQ= reqQ
        self.__pcs = pcs
        self.__cur_request_lock = utils.Lock()
        self.__cur_request = None

    @staticmethod
    def __upload_read_callback(self, reader):
        with self.__cur_request_lock:
            if self.__cur_request and self.__cur_request.is_cancel_upload():
                raise CancelUploadError(u'Only need stop current job.')

    def cancel_current_upload(self, request_id):
        with self.__cur_request_lock:
            if self.__cur_request:
                self.__cur_request.cancel_upload(request_id)

    def set_current_request(self, request):
        with self.__cur_request_lock:
            self.__cur_request = request

    def makeDir(self,path, remote_parent_dir, uuid_s, path_disk, request_id):
        logger.debug(u'Try to mkdir for %s in baidupcs'%path)
        db_req = request.Request(u'queryFileUploadInfo', dict(name=u'baidu', path=path, uuid=uuid_s, path_disk=path_disk, request_id=request_id))
        res = backupDbOperation.query_file_upload_info(db_req)

        if res.get(u'result') != 0:
            logger.error(u'Database error!')
            return False, res.get(u'error_code')

        if res.get(u'need_update') == 0:
            logger.debug(u'No need to upload file:%s'%path)
            return True,0

        db_msg = u'updateFileUploadInfo'
        db_dict = {}
        db_dict.update(dict(uuid=uuid_s, name=u'baidu',path=path, path_disk=path_disk, request_id=request_id))
        res = self.__pcs.make_dir(path, remote_parent_dir)
        if res.get(u'result') == 0:
            data = res.get(u'data')
            db_dict.update(dict(baidupcsfsid=data.get(u'baidupcsfsid'),   \
                                baidupcspath=data.get(u'baidupcspath'),  \
                                baidupcscode=0))
            db_req = request.Request(db_msg, db_dict)
            backupDbOperation.update_file_upload_info(db_req)
            ret = True, 0
        else:
            status_code = res.get(u'status')
            error_code = res.get(u'error_code')
            msg = res.get(u'error_msg')
            db_dict.update(dict(baidupcscode=error_code))
            db_req = request.Request(db_msg, db_dict)
            backupDbOperation.update_file_upload_info(db_req)
            ret = False, errors.transPCSErr2KortideErr(status_code,error_code)
            logger.error(u'Dir:%s was failed to mkdir,message:%s'%(path,msg))
        return ret

    def uploadSmallFile(self, path, remote_parent_dir, uuid_s, path_disk, request_id):
        db_msg = u'updateFileUploadInfo'
        db_dict = {}

        db_dict.update(dict(uuid=uuid_s, name=u'baidu', path=path, path_disk=path_disk, request_id=request_id))
        res = {}
        for i in range(3):
            res = self.__pcs.upload_small(path, 'overwrite', remote_parent_dir,
                                          read_callback=UploadAgentThrd.__upload_read_callback,
                                          read_callback_params=self)
            if res.get(u'result') == 0: break
            logger.debug(u'File %s upload failed, try to re-upload it....%d' % (path, i))
            time.sleep(3)

        if res.get(u'result') == 0:
            data = res.get(u'data')
            db_dict.update(dict(baidupcsmd5=data.get(u'baidupcsmd5'),    \
                                baidupcsfsid=data.get(u'baidupcsfsid'),   \
                                baidupcspath=data.get(u'baidupcspath'),   \
                                baidupcssize=data.get(u'baidupcssize'),  \
                                baidupcscode=0))
            ret = True,0
        else:
            status_code = res.get(u'status')
            error_code = res.get(u'error_code')
            msg = res.get(u'error_msg')
            db_dict.update(dict(baidupcscode=error_code))
            ret = False, errors.transPCSErr2KortideErr(status_code,error_code)
        logger.debug(u'upload small file:%s, result:%s, code:%d'%(path, ret[0],ret[1] ))
        db_req = request.Request(db_msg, db_dict)
        backupDbOperation.update_file_upload_info(db_req)
        return ret

    def uploadLargeFile(self,path, remote_parent_dir, uuid_s, path_disk, request_id):
        logger.debug(u'Large file not support yet, path:%s'%path)
        return False, errors.LARGE_FILE_SUPPORT

    def handleResponse(self, res, req):
        request_id = req.getId()
        if res.get(u'result') ==  0:
            req.status = request.STATUS_SUCCESS
        else:
            req.status = request.STATUS_FAILED
        error_code = res.get(u'error_code', 0)
        backupDbOperation.update_backup_record(request.Request(None, dict(request_id=request_id, status=req.status, error_code=error_code)))

    def try2UploadFile(self, path, remote_parent_dir, uuid_s, path_disk, request_id):
        logger.info(u'Try to upload file:%s'%path)
        db_req = request.Request(u'queryFileUploadInfo', dict(name=u'baidu', path=path, uuid=uuid_s, path_disk=path_disk, request_id=request_id))
        res = backupDbOperation.query_file_upload_info(db_req)

        if res.get(u'result') == 0:
            if res.get(u'need_update') != 0:
                f_size = os.path.getsize(path)
                if f_size >= self.__pcs.largest_size:
                    #logger.debug(u'File bigger than 2G, upload with uploadLargeFile()')
                    return self.uploadLargeFile(path, remote_parent_dir, uuid_s, path_disk, request_id)
                else:
                    #logger.debug(u'File smaller than 2G, upload with uploadSmallFile()')
                    return self.uploadSmallFile(path, remote_parent_dir, uuid_s, path_disk, request_id)
            else:
                logger.debug(u'No need to upload file:%s'%path)
                return True,0
        else:
            return False, res.get(u'error_code')

    def failedDirWithNoParentDir(self, dir, uuid_s, error_code, request_id):
        db_msg = u'updateFileUploadInfo'
        db_dict = dict( request_id=request_id, \
                        uuid=uuid_s,    \
                        name=u'baidu',  \
                        baidupcsfsid=0,   \
                        baidupcspath=None,  \
                        baidupcscode=error_code)
        for root, dirs, files, in os.walk(dir):
            root_dev_node, root_path_disk = utils.getDevNodeAndDiskRoot(root)
            logger.debug(u'Failing record in database')
            db_dict.update(dict(path=root,path_disk=root_path_disk))
            db_req = request.Request(db_msg, db_dict)
            backupDbOperation.update_file_upload_info(db_req)

            for f in files:
                logger.debug(u'Failing %s record in database')
                db_dict.update(dict(path=join(root,f),path_disk=join(root_path_disk,f)))
                db_req = request.Request(db_msg, db_dict)
                backupDbOperation.update_file_upload_info(db_req)

    def processReq(self, req):
        logger.debug(u'Try to processing one backup request')
        session, account = self.__pcs.get_session_info()
        if not account:
            logger.error(u'Not bind')
            res = {u'result':1,u'error_code':errors.UNBIND}
            self.handleResponse(res, req)
        elif not session:
            logger.debug(u'session expired')
            res = {u'result':1, u'error_code':errors.SESSION_EXPIRED}
            self.handleResponse(res, req)
        else:
            param = req.param
            path = param.get(u'path','')
            uuid_s = param.get(u'uuid','')
            path_disk = param.get(u'path_disk','')
            remote_parent_dir, f_name = split(path.rstrip(os.sep))
            remote_path = self.__pcs.transfer_local_path(path, remote_parent_dir)
            request_id = req.getId()

            req.status = request.STATUS_PROCESSING
            response = backupDbOperation.update_backup_record(request.Request(None, \
                                                                              dict(request_id=request_id, \
                                                                                   status=req.status, \
                                                                                   remote_path=remote_path)
                                                                            ))
            # get the number of database rows that are modified this time
            if not response.get(u'data', 0):
                logger.debug(u'no database rows are changed, considered as record had been canceled')
                return

            logger.debug(u'uploadAgentThrd processing request, path:%s, path_disk:%s, uuid_s:%s'%(path,path_disk,uuid_s))
            if isfile(path):
                status, code = self.try2UploadFile(path, remote_parent_dir, uuid_s, path_disk, request_id)
                if status == False:
                    res = {u'result':1, u'error_code':code}
                else:
                    res = {u'result':0, u'error_code':0}
                self.handleResponse(res, req)
            elif isdir(path):
                errors_flag = False
                for root, dirs, files in os.walk(path):
                    root_dev_node, root_path_disk = utils.getDevNodeAndDiskRoot(root)
                    logger.debug(u'root_path_disk:%s'%root_path_disk)
                    status,code = self.makeDir(root, remote_parent_dir, uuid_s, root_path_disk, request_id)
                    if status == False:
                        logger.error(u"Create dir %s failed, now failing all of it's sub-files"%root)
                        res = {u'result':1, u'error_code':code}
                        self.handleResponse(res, req)
                        errors_flag = True
                        self.failedDirWithNoParentDir(root, uuid_s, code, request_id)
                        break

                    for f in files:
                        status, code = self.try2UploadFile(join(root,f), remote_parent_dir, uuid_s, join(root_path_disk, f), request_id)
                        if status == False:
                            logger.debug(u'File %s upload failed, code:%d'%(f,code))
                            res = {u'result':1, u'error_code':code}
                            self.handleResponse(res, req)
                            errors_flag = True
                            break
                        else:
                            logger.debug(u'File %s uploaded to baidupcs'%f)
                    if errors_flag:
                        break
                if not errors_flag:
                    res = {u'result':0, u'data':''}
                    self.handleResponse(res, req)
            elif not exists(path):
                res = {u'result':1, u'error_code':errors.FILE_NOT_EXISTS}
                self.handleResponse(res, req)
            else:
                logger.error(u'%s isnot file or dir,only support to upload file and dir'%path)
                res = {u'result':1, u'error_code':errors.UNKNOWN_ERROR}
                self.handleResponse(res, req)

    def run(self):
        while True:
            try:
                req = self.__reqQ.get()
                if req.msg == u'Quit':
                    logger.debug(u'UploadTaskManager receive a quit msg, leaving now')
                    break
                self.set_current_request(req)
                self.processReq(req)
            except CancelUploadError, e:
                logger.debug(u'UploadAgentThrd: Current job has been cancelled.')
            except Exception, e:
                logger.error(u'UploadAgentThrd get one fatal error :%s' % str(e))
                logger.error(traceback.format_exc())
                res = {u'result':1, u'error_code':errors.UNKNOWN_ERROR}
                self.handleResponse(res, req)
        logger.debug(u'UploadTaskManager exist!')
