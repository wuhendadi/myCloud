##following are errors APP client should care about
BUSY = 1035                 #busy, try again later
SESSION_EXPIRED = 1036      #session expired, need to re-auth
ALREADY_BIND = 1037         #baiducloud already auth
INVALID_PARAMS = 1038       # params pass in are invalid
STORAGE_FULL = 1039         #baidupcs storage is full
PATH_INVALID = 1040         #path name is invalid
SERVER_ERROR = 1041         #servr error
NETWORK_ERROR = 1042        #network error
JOB_NOT_EXISTS = 1043       #job doesn't exists
DATABASE_ERROR =1044        #database operation error
TIMEOUT=1045                #request timeout
UNSUPPORTED_CLOUD = 1046    #unsupported cloud
FILE_NOT_EXISTS = 1047      #disk removed caused file not exists
UNKNOWN_ERROR = 1048        #unkown error
UNSUPPORTED_METHODS = 1049  #unsupported methods
DISK_NOT_MOUNTED = 1050     #disk is not mounted
UNBIND = 1051             #account not bind
AUTH_PENDING = 1052         #User not complete auth
AUTH_DECLINED = 1053        #user declined in auth
MAX_REQUESTS = 1054           #max requests reached

LARGE_FILE_SUPPORT = 9999

# used in code
DATABASE_TABLE_ALREADY_EXIST = 1200  # table already exists
DATABASE_TABLE_NOT_EXIST = 1201 # table not exists

#following errors is used in code
PCS_AUTH_REFRESH_EXPIRED = u'expired_token'
PCS_AUTH_SLOW_DOWN = u'slow_down'
PCS_AUTH_PENDING = u'authorization_pending'
PCS_AUTH_DECLINED = u'authorization_declined '

PCS_FILE_EXISTS = 31061
PCS_FILE_NOT_EXISTS = 31066
PCS_PPATH_NOT_EXISTS = 31063
PCS_REQUEST_LIMIT = 31219 #request exceed limit

def map_client_error(status, pcsErrCode):
    if status == 400:
        if pcsErrCode == 31112:  #exceed quota
            kortide_code = STORAGE_FULL
        elif pcsErrCode == 31062:#file name is invalid
            kortide_code = PATH_INVALID
        else:
            kortide_code = INVALID_PARAMS
    elif pcsErrCode == 31218: #storage exceed limit
        kortide_code = STORAGE_FULL
    elif pcsErrCode in [110,31044]: #user is not authorized or Access token invalid or no longer valid
        kortide_code = SESSION_EXPIRED
    else:
        kortide_code = UNKNOWN_ERROR
    return kortide_code

def map_server_error(status, pcsErrCode):
    if pcsErrCode == 31021:#network error
        kortide_code = NETWORK_ERROR
    else:
        kortide_code = SERVER_ERROR
    return kortide_code

def transPCSErr2KortideErr(status, pcsErrCode):

    if status in [400, 401, 403, 404]:
        code = map_client_error(status,pcsErrCode)
    elif status == [500, 501, 503]:
        code = map_server_error(status,pcsErrCode)
    else:
        code = UNKNOWN_ERROR
    return  code



