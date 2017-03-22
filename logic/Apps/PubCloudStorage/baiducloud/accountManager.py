import pcsAuth
import threading
import time
import UtilFunc
import shelve
import pcsAuth
import json
import repeatable
import errors
from .. import request

SESSION_EXPIRED         = u'SessionExpired'
BIND_CLOUD_ACCOUNT      = u'BindCloudAccount'
UNBIND_CLOUD_ACCOUNT    = u'UnbindCloudAccount'
GET_CLOUD_ACCOUT        = u'GetCloudAccount'
GET_TOKEN               = u'GetToken'
UNBINDED                = u'unbinded'

logger = UtilFunc.getLogger()
REFRESH_INTERVAL =  24 * 60 *60 #one day, in seconds
REFRESH_TIMER_T =  1 * 60 * 60 #check every one hour

Refresh_Timer_Thrd = None

class AccountManager(threading.Thread):
    def __init__(self, queue, generalQ, pcs):
        threading.Thread.__init__(self)
        self.__lock = threading.Lock()
        self.__q = queue
        self.__generalQ = generalQ
        self.pAuth = pcsAuth.PcsAuth(pcs)

    def setSessionState(self, state):
        self.__lock.acquire()
        self.__sessionState = state
        self.__lock.release()

    def getSessionState(self):
        self.__lock.acquire()
        state = self.__sessionState
        self.__lock.release()

    def handleSessionExpiredReq(self, req):
        logger.debug(u'Session Expired Exception! Invalid session!')
        self.pAuth.clear_access_token()
        return {u'result':0, u'message':''}

    def bindCloudAccount(self):
        res = self.pAuth.device_auth()
        if res.get(u'result') == 0:
            user_code = res.get(u'data').get(u'user_code')
            auth_url = res.get(u'data').get(u'verification_url')
            d = dict(verification_url=auth_url, user_code=user_code)
            ret = {u"result":0, u"data":d}
            logger.debug(u'Binding baidupcs, verif_url:%s, user_code:%s'%(auth_url,user_code))
        else:
            ret = res
        return json.dumps(ret)

    def unbindCloudAccount(self):
        logger.debug(u'Send delete records request to general queue')
        unbinded_req = request.Request(UNBINDED,None)
        self.__generalQ.put(unbinded_req)
        unbinded_req.getResponse()

        logger.debug(u'Unbinding baidupcs!')
        self.pAuth.invalid_AccessToken()
        res = {u"result":0, u"data":""}
        return json.dumps(res)

    def getCloudAccount(self):
        logger.debug(u'Getting user nickname!')
        res = self.pAuth.get_CloudAccount()
        return json.dumps(res)

    def getToken(self):
        res = self.pAuth.read_AccessToken()
        return json.dumps(res)

    def __refreshToken(self):
        logger.debug(u'Try to refreshing Token!')
        res = self.pAuth.refresh_AccessToken()

    def checkNeed2RefreshToken(self):
        logger.debug(u'Checking whether we need to refresh access_token!')
        state = self.pAuth.get_state()
        if state != u'validated':
            logger.debug(u'Session state is %s, no need to check!'%state)
            return

        s = shelve.open(pcsAuth.AT_file)
        refreshed = s.get(u'refreshed')
        s.close()
        try:
            now_time = int(time.time())
            delta = now_time - refreshed
        except ValueError:
            logger.warn(u'Errors happens, force to refresh token!')
            delta = REFRESH_INTERVAL
        if delta < 0 or delta >= REFRESH_INTERVAL:
            logger.warn(u'Need to refresh Token right now!')
            self.__refreshToken()
        else:
            logger.debug('Refresh delta is %d, no need to refresh current!'%delta)
        logger.debug(u'Check Done!')

    def run(self):
        global Refresh_Timer_Thrd
        global REFRESH_TIMER_T
        Refresh_Timer_Thrd = repeatable.RepeatableTimer(REFRESH_TIMER_T,self.checkNeed2RefreshToken)
        Refresh_Timer_Thrd.start()
        while True:
            try:
                req = self.__q.get()
                logger.debug(u'AccountManager thread receiving message %s!'%req.msg)
                if req.msg == SESSION_EXPIRED:
                    res = self.handleSessionExpiredReq(req)
                elif req.msg == BIND_CLOUD_ACCOUNT:
                    res = self.bindCloudAccount()
                elif req.msg == UNBIND_CLOUD_ACCOUNT:
                    res = self.unbindCloudAccount()
                elif req.msg == GET_CLOUD_ACCOUT:
                    res = self.getCloudAccount()
                elif req.msg == GET_TOKEN:
                    res = self.getToken()
                elif req.msg == u'Quit':
                    break
                else:
                    res = None
                    logger.warn(u'Unsupported message:%s, ignored!'%req.msg)

                req.setResponseData(res)
                req.done()
            except Exception, e:
                logger.error(u'accountManager get a fatal error %s'%str(e))
        logger.warn(u'leaving AccountManager thread!')
        Refresh_Timer_Thrd.stop()
