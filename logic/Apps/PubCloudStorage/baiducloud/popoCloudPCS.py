import sys
import baidupcs
import threading
import UtilFunc
import pcsAuth
import shelve
import os
from os.path import split, join
import json
import requests
from functools import wraps
import errors
from .. import request

logger = UtilFunc.getLogger()

LARG_FILE_SIZE = 2 *1024 * 1024 * 1024
LARGE_FILE_CHUNK_SIZE = 10 * 1024 * 1024

def handleExceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        except requests.ConnectionError:
            response = {u'result':1, u'error_msg':u'network error',  u'error_code':errors.NETWORK_ERROR}
        except baidupcs.InvalidToken:
            PopoCloudPCS.expired_session(*args, **kwargs)
            PopoCloudPCS.sendExpiredSessionMsg(*args, **kwargs)
            response = {u'result':1, u'error_msg':u'invalid session', u'error_code':errors.SESSION_EXPIRED}
        except requests.exceptions.Timeout:
            response = {u'result':1, u'error_msg':u'invalid session', u'error_code':errors.NETWORK_ERROR}
        return response
    return wrapper

class PopoCloudPCS(baidupcs.PCS):
    def __init__(self, accMgrQ):
        self.__l = threading.Lock()
        self.__session_valid_e = threading.Event()
        self.largest_size = LARG_FILE_SIZE
        self.__has_account_e = threading.Event()
        self.__accoutMgrQ = accMgrQ

        s = shelve.open(pcsAuth.AT_file)
        at = s.get('access_token')
        has_account = s.get('account_bind',False)
        self.__remote_workspace = s.get('workspace')
        s.close()

        if has_account:
            self.__has_account_e.set()
        else:
            self.__has_account_e.clear()

        if at:
            baidupcs.PCS.__init__(self, at)
            self.__session_valid_e.set()
        else:
            baidupcs.PCS.__init__(self, u'invalid_token')
            self.__session_valid_e.clear()

    def update(self):
        self.__l.acquire()
        s = shelve.open(pcsAuth.AT_file)
        self.access_token = s.get('access_token')
        self.__remote_workspace = s.get('workspace')
        has_account = s.get('account_bind', False)
        s.close()

        if has_account:
            self.__has_account_e.set()
        else:
            self.has_account.clear()

        if self.access_token:
            self.__session_valid_e.set()
        else:
            self.__session_valid_e.clear()
        self.__l.release()

    def get_session_info(self):
        session_valid = self.__session_valid_e.wait(timeout=0)
        has_account = self.__has_account_e.wait(timeout=0)
        return session_valid, has_account

    def expired_session(self,*args, **kwarg):
        self.__session_valid_e.clear()

    def unbind_account(self):
        self.__has_account_e.clear()

    def sendExpiredSessionMsg(self, *args, **kwargs):
        req = request.Request(u'SessionExpired', None)
        self.__accoutMgrQ.put(req)

    @handleExceptions
    def upload_small(self, local_path, ondup, remote_parent_dir, **kwargs):
        """
        read_callback(read_callback_params, BufferReader): used to cancel upload file.
        """
        remote_p = self.transfer_local_path(local_path, remote_parent_dir)
        logger.debug(u'upload to %s'%remote_p)
        res = self.upload(remote_p, open(local_path,u'rb'), ondup, timeout=120, **kwargs)
        status = res.status_code
        data = json.loads(res.content)
        if status == 200:
            d = dict(baidupcsmd5=data.get(u'md5'),baidupcsfsid=data.get(u'fs_id'), baidupcspath=data.get(u'path'),baidupcssize=data.get(u'size'))
            response = {u'result':0, u'data':d}
        else:
            msg = data.get(u'error_msg')
            code = data.get(u'error_code')
            response = {u'result':1,  u'error_msg':msg, u'error_code':code, u'status':status}
        return response

    @handleExceptions
    def upload_large_file(self, local_path, remote_parent_dir, ondup, **kwargs):
        """
        File size should > 2GB
        """

        remote_path = self.transfer_local_path(local_path, remote_parent_dir)
        logger.debug(u'Upload large file, local: {0}, remote: {1}'.format(local_path, remote_path))

        stop_event = kwargs.get('stop_event')
        last_block_list = kwargs.get('last_block_list')

        def get_error_response(status_code, content):
            return {u'result': 1,
                    u'error_msg': content.get(u'error_msg'),
                    u'error_code': content.get(u'error_code'),
                    u'status': status_code}

        with open(local_path, u'rb') as fd:
            block_list = []

            if last_block_list:
                block_list.extend(last_block_list)
                fd.seek(LARGE_FILE_CHUNK_SIZE * len(last_block_list))

            while True:
                data = fd.read(LARGE_FILE_CHUNK_SIZE)
                if not data: break
                res = self.upload_tmpfile(data)
                content = json.loads(res.content)
                if res.status_code != 200:
                    return get_error_response(res.status_code, content)
                md5 = content.get(u'md5')
                block_list.append(md5)
                del data

                if stop_event and stop_event.is_set():
                    return {u'result': 2,
                            u'block_list': block_list}

            res = self.upload_superfile(remote_path, block_list, ondup)
            content = json.loads(res.content)
            print repr(content)
            if res.status_code != 200:
                return get_error_response(res.status_code, content)
            return {u'result': 0,
                    u'data': {u'baidupcsmd5': content.get(u'md5'),
                              u'baidupcsfsid': content.get(u'fs_id'),
                              u'baidupcspath': content.get(u'path'),
                              u'baidupcssize': content.get(u'size'), }}

    @handleExceptions
    def make_dir(self, local_path, remote_parent_dir):
        remote_p = self.transfer_local_path(local_path, remote_parent_dir)
        res = self.mkdir(remote_p)
        status = res.status_code
        data = json.loads(res.content)
        if status == 200:
            d = dict(baidupcsmd5=0,baidupcsfsid=data.get(u'fs_id'), baidupcspath=data.get(u'path'))
            response = {u'result':0, u'data':d}
        elif data.get(u'error_code') == errors.PCS_FILE_EXISTS:
            res_sub = self.meta(remote_p)
            sub_data = json.loads(res_sub.content)
            if res_sub.status_code == 200:
                meta_d = sub_data.get(u'list')[0]
                d = dict(baidupcsmd5=0,baidupcsfsid=meta_d.get(u'fs_id'), baidupcspath=meta_d.get(u'path'))
                response = {u'result':0, u'data':d}
            else:
                msg = sub_data.get(u'error_msg')
                code = sub_data.get(u'error_code')
                response = {u'result':1, u'error_msg':msg, u'error_code':code, u'status':status}
        else:
            msg = data.get(u'error_msg')
            code = data.get(u'error_code')
            response = {u'result':1, u'error_msg':msg, u'error_code':code, u'status':status}
        return response

    def transfer_local_path(self, local_path, remote_parent_dir):
        local_path.rstrip(os.sep)
        r_path = local_path.replace(remote_parent_dir,self.__remote_workspace)
        #r_path = join(self.__remote_workspace, join(remote_parent_dir,f_name))

        return unicode(r_path.rstrip(os.sep))
