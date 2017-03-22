# -*- coding: utf-8 -*-
#author: ZJW

import os
import uuid
import time
import httplib
import urllib
import json
import struct
import PopoConfig
import UtilFunc
import cherrypy
import types
import base64
import PostStatic
import CSTunnel
import ProfileFunc
import Log

from zipstream import ZipStream

tokens = {}

noauths = {'/api/music':'/stream',
           '/api/video':'/stream',
           '/api/camerapp':'/stream',
           }
 
NO_CHECKDISK_API = []

def http_methods_allowed(methods=['GET','POST','DELETE','PUT','PATCH']):
    method = cherrypy.request.method.upper()
    if method not in methods:
        cherrypy.response.headers['Allow'] = ", ".join(methods)
        raise cherrypy.HTTPError(405)   

cherrypy.tools.allow = cherrypy.Tool('on_start_resource', http_methods_allowed)

def noauth(f):
    """A decorator that set the auth.ignore config variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        f._cp_config['auth.ignore'] = True
        return f
    return decorate(f)

def checkAuth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    
    if hasattr(cherrypy.request, 'json'):
        cherrypy.request.params.update(cherrypy.request.json)
    return True
    if cherrypy.request.script_name in noauths.keys() and noauths[cherrypy.request.script_name] in cherrypy.request.path_info:
        return True
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    headers = cherrypy.request.headers
    authorization = headers.get('authorization', None)
    
    if not authorization:
        token = cherrypy.request.params.get('token', headers.get('token', None))
        clientId = cherrypy.request.params.get('clientId', headers.get('clientId', None))
        if not token or not clientId:
            raise cherrypy.HTTPError(401)
    else:
        try:
            tokenType,tokenStr = authorization.split()                   
            if tokenType == 'guestToken': 
                if ProfileFunc.isShareIdEnable(tokenStr):
                    return True
                else:
                    raise cherrypy.HTTPError(401)
            elif tokenType == 'Token':
                clientId, token = base64.decodestring(tokenStr).split(':')
            else:
                raise cherrypy.HTTPError(401)
    
        except Exception,e:
            Log.exception('CheckAuth Exception! Reason[%s]'%e)
            raise cherrypy.HTTPError(401)
        
    if not UtilFunc.toBoolean(verifyToken(token, clientId)):
        raise cherrypy.HTTPError(401)
    
    if not cherrypy.request.script_name in NO_CHECKDISK_API and not ProfileFunc.GetBoxDisks():
        raise cherrypy.HTTPError(465, 'Not Exist Disk')
    
    return True
    
        
cherrypy.tools.auth = cherrypy.Tool('before_handler', checkAuth)

def jsonResult(ret):
    if ret == None:
        return callBack('{}')

    if isinstance(ret, types.DictType):
        return callBack(json.dumps(ret))

    if isinstance(ret, types.ListType):
        return callBack(json.dumps({"data":ret}))
    
    return callBack(json.dumps(ret))

def httpErr(num):
    cherrypy.response.status = num
    
def httpStatus(num):
    cherrypy.response.status = num

def callBack(ret):
    cherrypy.response.headers['Content-Type'] = 'application/json'
    jsonpCallback = cherrypy.request.params.get("jsonpCallback")
    if jsonpCallback:
        return jsonpCallback + "(" + ret + ")"
    else:
        return ret
    
def checkId(arg, dict):
    if arg: mid = arg[0] 
    else: raise cherrypy.HTTPError(460, 'Bad Parameters')
    if not dict.has_key(mid):
        raise cherrypy.HTTPError(464, 'Not Exist')
    return mid
    
#------------------------------------------------------------------------------------------
def addToken(clientId, token, expire=PopoConfig.SESSION_TIMEOUT):
    tokens.setdefault(clientId, {'token':token, 'time':time.time(), 'expire':expire})

def revokToken(tokens):
    for clientId in tokens.keys():
        if tokens[clientId].get('token') in tokens:
            del tokens[clientId]
            
def refreshToken():
    headers = cherrypy.request.headers
    clientId = cherrypy.request.params.get('clientId', headers.get('clientId', None))
    if tokens.has_key(clientId):
        tokens[clientId].update({'time':time.time(),'expire':PopoConfig.SESSION_TIMEOUT})
        
def changeStatus(status='Updating'):
    msg = {'status':status,'description':u'设备正在升级，请在几分钟后重试连接设备'} 
    return getRstAck(msg, CSTunnel.STATUS, None, None)

def getShareUrl(shareId, flag, validity):
    msg = {'shareId':shareId,'hasCode':flag,'expire':validity}
    return getRstAck(msg, CSTunnel.CREATESHORTURL, shareId, 'urlId')
        
def verifyToken(token, clientId):
    if UtilFunc.isLinuxSystem() and UtilFunc.toBoolean(PopoConfig.ViaEcs):
        from Sitelib import ecs_module
        Log.info("ViaEcs To verifyToken")
        is_valid, result = ecs_module.verify_token(clientId, token)
        Log.info("ViaEcs To verifyToken SuccessFull!")
        return str(is_valid)
    else:
        if tokens.has_key(clientId):
            curr_time = time.time()
            while tokens.has_key(clientId) and tokens[clientId] == {}:
                if time.time() - curr_time >= 30:
                    break
                time.sleep(0.1)
            if not tokens.has_key(clientId):
                checkAuth()
            elif tokens[clientId].get('token') == token:
                if time.time() - tokens[clientId].get('time') > tokens[clientId].get('expire'):
                    del tokens[clientId]
                    return False
                else:
                    tokens[clientId].update({'time':time.time(),'expire':PopoConfig.SESSION_TIMEOUT})
                    return True
        tokens[clientId] = {}
        verifyRet = getRstAck({'token':token,'clientId':clientId}, CSTunnel.VERIFYTOKEN, token, 'valid')
        if UtilFunc.toBoolean(verifyRet):
            tokens[clientId].update({'token':token,'time':time.time(),'expire':PopoConfig.SESSION_TIMEOUT})
            return True
        else:
            del tokens[clientId]
            return False

def getRstAck(msg, msgType, kid, key):
    if UtilFunc.isLinuxSystem() and UtilFunc.toBoolean(PopoConfig.ViaEcs):
        conn = ProfileFunc.getMainServer().ecsModule
        from Sitelib import ecs_module
        msg = json.dumps(msg)
        Log.info('ViaEcs SendHubMsg')
        result = ecs_module.send_hub_message(msgType, struct.pack('%ds'%len(msg), msg))
        Log.info('ViaEcs SendHubMsg SuccessFull')
        if result != 0: return None
    else:
        conn = ProfileFunc.getMsgChannel()
        conn.send(msg, msgType)
         
    current = time.time()
    while kid:
        if conn.retdict.has_key(kid):
            body = conn.retdict.pop(kid)
            return body.get(key, None)
        if time.time() - current >= 30:
            return None
        time.sleep(0.5)
    
# def verifyToken(token, clientId):
#     msg = {'token':token,'clientId':clientId}
#     return getRstAck(msg, CSTunnel.VERIFYTOKEN, token, 'valid')
#         
# def getRstAck(msg, msgType, kid, key):
#     conn = ProfileFunc.getMsgChannel()
#     conn.send(msg, msgType)
#         
#     current = time.time()
#     while True:
#         if conn.retdict.has_key(kid):
#             body = conn.retdict.pop(kid)
#             return body.get(key, None)
#         if time.time() - current >= 30:
#             return None
#         time.sleep(0.5)

def DownloadFolderZip(folderPath):
    if not os.path.isdir(folderPath):
        raise cherrypy.HTTPError(460, 'Bad Parameter')

    folderPath = ProfileFunc.slashFormat(folderPath)
    
    filename = os.path.basename(folderPath)
    filename = filename+'.zip'
    request = cherrypy.serving.request
    filename = UtilFunc.StringUrlEncode(filename)
    
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Last-Modified'] = time.time()
    User_Agent = request.headers.get('User-Agent')
    if 'Firefox' in User_Agent: 
        response.headers['Content-Disposition'] = 'attachment;filename*="%s"' %filename
    else:
        response.headers['Content-Disposition'] = 'attachment;filename="%s"' %filename    
        
    zipobj = ZipStream(folderPath)
    return zipobj.__iter__()

def DownloadFile(filePath): 
    if not ProfileFunc.GetBoxDisks():
        raise cherrypy.HTTPError(464, 'Not Exist')
    
    filePath = ProfileFunc.slashFormat(filePath)
    if UtilFunc.isShorcut(filePath):
        filePath = UtilFunc.getShortcutRealPath(filePath)

    filePathShort = UtilFunc.getShortPath(filePath)

    if os.path.isdir(filePathShort):
        raise cherrypy.HTTPError(460, 'Bad Parameter')
    elif os.path.exists(filePathShort):
        filename = os.path.basename(filePath)
        filename = UtilFunc.StringUrlEncode(filename)
        return PostStatic.serve_download(filePathShort, filename)
    else:
        raise cherrypy.HTTPError(464, 'Not Exist')

def socketSend(host,port,msg):
    import socket
    try:
        tcp_cc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_cc.connect((host,port))
        tcp_cc.send(msg)
        ret = tcp_cc.recv(1024)
        tcp_cc.close()
        return ret
    except Exception,e:
        Log.error("SendSocket Failed! Reason[%s]"%e)
        return None
    
    