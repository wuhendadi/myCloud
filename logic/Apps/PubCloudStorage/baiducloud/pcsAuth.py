#coding = utf8

import shelve
import os
import json
import UtilFunc
import time
import threading
import requests
import sys
import errors
from popocloudApp import API_Key, API_Secret, APP_Root

serialNo = UtilFunc.getSN()

AUTH_STATE_UNBIND = 'unbind'
AUTH_STATE_EXPIRED = 'expired'
AUTH_STATE_AUTHENTICATING = 'authenticating'
AUTH_STATE_REFRESHING = 'refreshing'
AUTH_STATE_VALIDATED = 'validated'
logger = UtilFunc.getLogger()
AT_const_param = '&client_id=' + API_Key + '&client_secret=' + API_Secret
AT_file = '/data/popoCloudData/CloudBackup/baidupcs/pcsAT.dat'
time_fmt = '%m-%d-%y'

CONNECTION_OK = 0
CONNECTION_FAILED = 1
CONNECTION_EXCEPTION = 3


class AuthEvent():
    def __init__(self, interval=5):
        self.__e = threading.Event()
        self.errCode = 0
        self.interval = 2 * interval

    def wait(self):
        self.__e.clear()
        self.__e.wait(timeout=self.interval)
        return self.errCode

    def set(self, code):
        self.errCode = code
        self.__e.set()

class PcsAuth():
    def __init__(self, pcs):
        s = shelve.open(AT_file)
        self.__state = s.get('session_state','unbind')
        s.close()
        self.__pcs = pcs
        self.expires_in = None
        self.interval = 5
        self.device_code = None
        self.__l = threading.Lock()
        self.__TokenL = threading.Lock()
        self.user_code = None
        self.verif_url = None
        self.auth_e = None

    def get_state(self):
        self.__l.acquire()
        state =  self.__state
        self.__l.release()
        return state

    def set_state(self, state):
        self.__l.acquire()
        self.__state = state
        self.__l.release()

    def device_auth(self):
        if self.get_state() in [AUTH_STATE_VALIDATED,AUTH_STATE_REFRESHING]:
            logger.warn(u'Session state did not expired, ignore this bind request!')
            return {u'result':1,u'error_code':errors.ALREADY_BIND}

        if self.get_state() == AUTH_STATE_AUTHENTICATING:
            res = {u'result':0,u'data':{\
                                            u'user_code':self.user_code, \
                                            u'verification_url':self.verif_url}
                    }
            return res

        logger.debug(u'Sending device auth requests to baidupcs server!')
        url = u'https://openapi.baidu.com/oauth/2.0/device/code' \
                + u'?client_id=' + API_Key                              \
                + u'&response_type=device_code&scope=basic,netdisk'
        result, data = self.requests_get(url)
        if result == CONNECTION_FAILED:
            error = data[u'error']
            err_msg = data[u'error_description']
            self.user_code = None
            self.verif_url = None
            error_code = errors.UNKNOWN_ERROR
        elif result == CONNECTION_OK:
            self.device_code = data[u'device_code']
            self.user_code = data[u'user_code']
            self.verif_url = data[u'verification_url']
            self.expires_in = data[u'expires_in']
            self.interval = data[u'interval']
            self.set_state(AUTH_STATE_AUTHENTICATING)
            self.auth_e = AuthEvent(self.interval)
            threading.Thread(target=self.query_AuthResult).start()
        else:
            self.user_code = None
            self.verif_url = None
            err_msg = data
            error_code = errors.NETWORK_ERROR

        if not self.user_code or not self.verif_url:
            logger.debug(u'Device auth failed, message:%s'%err_msg)
            res = {u'result':1, u'error_code':error_code}
        else:
            logger.debug(u'Device auth success, got verification_url and user_code ')
            res = {u'result':0,u'data':{\
                                            u'user_code':self.user_code, \
                                            u'verification_url':self.verif_url}
                }
        return res

    def query_AuthResult(self):
        while True:
            res = self.get_AccessToken()
            result = res.get(u'result')
            error_code = res.get(u'error_code',0)
            self.auth_e.set(error_code)
            if result == 1:
                if error_code in [errors.AUTH_PENDING, errors.BUSY, errors.NETWORK_ERROR]:
                    logger.debug(u'User not finish auth or slow down, Try again %s seconds later, err_code:%d'%(self.interval,error_code))
                    time.sleep(self.interval)
                else:
                    #print error_code
                    self.set_state(AUTH_STATE_UNBIND)
                    self.user_code = None
                    self.verif_url = None
                    logger.debug(u'Auth failed!')
                    break
            else:
                logger.debug(u'Auth success!')
                break
        else:
            logger.debug(u'Exiting previous auth thread')

    def refresh_AccessToken(self):
        state = self.get_state()
        if state != AUTH_STATE_VALIDATED:
            logger.warn(u'Should refresh token under validated state! curr_state:%s'%state)
            return

        self.set_state(AUTH_STATE_REFRESHING)
        s = shelve.open(AT_file, 'r')
        refresh_token = s['refresh_token']
        s.close()
        logger.debug(u'Sending refresh access token request to baidupcs server!')
        url =   u'https://openapi.baidu.com/oauth/2.0/token'  \
                u'?grant_type=refresh_token&refresh_token=' \
                + refresh_token + AT_const_param
        result, data = self.requests_get(url)
        if result == CONNECTION_FAILED:
            error = data[u'error']
            message =data[u'error_description']
            logger.error(u'Refresh Failed, message:%s'%message)
        elif result == CONNECTION_OK:
            logger.debug(u'Success! Trying to save access_token')
            self.save_AccessToken(data)
        else:
            logger.error(u'Network error,refresh Failed')

    def get_AccessToken(self):
        if self.get_state() in [AUTH_STATE_VALIDATED,AUTH_STATE_REFRESHING]:
            return self.read_AccessToken()
        elif self.get_state() == AUTH_STATE_EXPIRED:
            return {u'result':1, u'error_code':errors.SESSION_EXPIRED}
        elif self.get_state() == AUTH_STATE_UNBIND:
            return {u'result':1, u'error_code':errors.UNBIND}

        logger.debug(u'Sending get access token request to baidupcs server!')
        url =   u'https://openapi.baidu.com/oauth/2.0/token'  \
                + u'?grant_type=device_token&code=' \
                + self.device_code + AT_const_param
        result, data = self.requests_get(url)
        if result == CONNECTION_FAILED:
            err = data[u'error']
            if err == errors.PCS_AUTH_PENDING:
                return {u'result':1, u'error_code':errors.AUTH_PENDING}
            elif err == errors.PCS_AUTH_DECLINED:
                return {u'result':1, u'error_code':errors.AUTH_DECLINED}
            elif err == errors.PCS_AUTH_SLOW_DOWN:
                return {u'result':1, u'error_code':errors.BUSY}
            else:
                logger.debug(data[u'error_description'])
                self.__pcs.expired_session()
                self.__pcs.unbind_account()
                self.set_state(AUTH_STATE_UNBIND) #user refuse to auth or other tech error
                return {u'result':1, u'error_code':errors.UNKNOWN_ERROR}
        elif result == CONNECTION_OK:
            self.save_AccessToken(data)
            self.get_CloudAccount()
            self.creat_Workspace()
            return {u'result':0, u'error_code':0}
        else:
            logger.error(u'Try to get access_token later!')
            return {u'result':1, u'error_code':errors.NETWORK_ERROR}

    def invalid_AccessToken(self):
        if self.get_state() not in [AUTH_STATE_REFRESHING, AUTH_STATE_VALIDATED]:
            logger.error(u'Try to invalidate session in invalid state')
        else:
            at_res = self.read_AccessToken()
            if at_res.get(u'result') == 0:
                at = at_res.get(u'access_token')
            else:
                at = u''
            logger.debug(u'Sending expired Session request to baidupcs server')
            url =   u'https://openapi.baidu.com/rest/2.0/passport/auth/expireSession' \
                    + u'?access_token='
            self.requests_get(url)
        pcs_s = shelve.open(AT_file)
        pcs_s.clear()
        pcs_s.close()
        self.set_state(AUTH_STATE_UNBIND)
        self.__pcs.expired_session()
        self.__pcs.unbind_account()
        return

    def clear_access_token(self):
        self.__TokenL.acquire()
        pcs_s = shelve.open(AT_file)
        pcs_s.update(dict(access_token=None))
        pcs_s.close()
        self.__TokenL.release()
        self.set_state(AUTH_STATE_EXPIRED)

    def get_CloudAccount(self):
        if self.get_state() == AUTH_STATE_AUTHENTICATING:
            logger.warn(u'Busy! Account is under authenticating')
            error_code = self.auth_e.wait()
            if error_code == errors.AUTH_PENDING:
                logger.debug(u'auth pending, user hasnot finish it')
                return {u'result':1, u'error_code':errors.AUTH_PENDING}
            elif error_code in [errors.BUSY, errors.NETWORK_ERROR]:
                logger.debug(u'auth busy, try again later')
                return {u'result':1, u'error_code':errors.BUSY}
            else:
                #auth failed or success follow the following logic
                pass

        if self.get_state() == AUTH_STATE_UNBIND:
            logger.error(u'Has not bind any account!')
            return {u'result':1, u'error_code':errors.UNBIND}

        if self.get_state() == AUTH_STATE_EXPIRED:
            logger.error(u'Session Expired!')
            return {u'result':1, u'error_code':errors.SESSION_EXPIRED}

        s = shelve.open(AT_file)
        uname = s.get('user_name', None)
        s.close()
        if uname:
            logger.debug(u'Get user nickname from local!')
            res = {u'result':0, u'data':[dict(user_name=uname)]}
            #print res
            return res

        response = self.read_AccessToken()
        if response.get(u'result') != 0:
            res = response
        else:
            at = response.get(u'access_token')
            logger.debug(u'Sending get nickname request to baidupcs server')
            url = u'https://openapi.baidu.com/rest/2.0/passport/users/getLoggedInUser' \
                    + u'?access_token=' + at
            result, data = self.requests_get(url)
            if result == CONNECTION_FAILED:
                error_code = data[u'error_code']
                if error_code == 110:
                    res = {u'result':1, u'error_code':errors.SESSION_EXPIRED}
                else:
                    res = {u'result':1, u'error_code':errors.UNKNOWN_ERROR}
            elif result == CONNECTION_OK:
                user_name = data[u'uname']
                d = {u'user_name':user_name}
                res = {u'result':0, u'data':[d]}
                self.__TokenL.acquire()
                s = shelve.open(AT_file)
                s.update(dict(user_name=user_name))
                s.close()
                self.__TokenL.release()
            else:
                res = {u'result':1, u'error_code':errors.NETWORK_ERROR}
        return res

    def save_AccessToken(self, data):
        global time_fmt
        global serialNo

        if self.get_state()  not in [AUTH_STATE_AUTHENTICATING,AUTH_STATE_REFRESHING]:
            logger.error(u'saving access_token in an invalid state')
            return

        self.__TokenL.acquire()
        pcs_s = shelve.open(AT_file)
        pcs_s.clear()
        pcs_s.update(dict(access_token=data[u'access_token']))
        pcs_s.update(dict(expires_in=data[u'expires_in']))
        pcs_s.update(dict(refresh_token=data[u'refresh_token']))
        pcs_s.update(dict(scope=data[u'scope']))
        pcs_s.update(dict(session_key=data[u'session_key']))
        pcs_s.update(dict(session_secret=data[u'session_secret']))
        pcs_s.update(dict(session_state=AUTH_STATE_VALIDATED))
        pcs_s.update(dict(account_bind=True))
        # add time every time update AT
        refresh_at = int(time.time())
        pcs_s.update(dict(refreshed=refresh_at))
        # add box serialNo
        pcs_s.update(dict(serialNo=serialNo))
        logger.debug(u'Update auth data to:%s'%pcs_s)
        pcs_s.close()

        app_root = APP_Root
        box_dir = u'Box-' + serialNo
        box_workSpace = os.path.join(app_root, box_dir)
        pcs_s = shelve.open(AT_file)
        pcs_s.update(dict(workspace=box_workSpace))
        pcs_s.close()

        self.__TokenL.release()

        logger.debug(u'Update session!')
        self.__pcs.update()  ##update session
        self.set_state(u'validated')

    def read_AccessToken(self):
        if self.get_state() == AUTH_STATE_EXPIRED:
            return {u'result':1, u'error_code':errors.SESSION_EXPIRED}
        elif self.get_state() == AUTH_STATE_UNBIND:
            return {u'result':1, u'error_code':errors.UNBIND}
        elif self.get_state() == AUTH_STATE_AUTHENTICATING:
            return {u'result':1, u'error_code':errors.AUTH_PENDING}

        self.__TokenL.acquire()
        pcs_s = shelve.open(AT_file)
        AT = pcs_s.get('access_token')
        pcs_s.close()
        self.__TokenL.release()
        return {u'result':0, u'access_token':AT}

    def creat_Workspace(self):
        self.__TokenL.acquire()
        pcs_s = shelve.open(AT_file)
        box_workSpace = pcs_s.get('workspace')
        pcs_s.close()
        self.__TokenL.release()

        self.__pcs.mkdir(box_workSpace)

    def requests_get(self, url):
        try:
            res = requests.get(url,verify=False)
            logger.debug(u'Get requests response:%s'%res.content)
            print res.content
            data = json.loads(res.content)
            status = res.status_code
            if status == 200:
                return CONNECTION_OK, data
            else:
                return CONNECTION_FAILED, data
        except requests.ConnectionError, e:
            logger.error(e)
            return CONNECTION_EXCEPTION, u'Network Error'


