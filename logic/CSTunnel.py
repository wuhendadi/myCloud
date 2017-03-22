# -*- coding: utf-8 -*-
#author:ZJW

import os, time
import json, struct
import socket, select
import thread, threading
import Command
import PopoConfig
import UtilFunc
import WebFunc
import ProfileFunc
import Log

from Sitelib.NetTunnel import NetTunnel
from Sitelib.constant import *

socket.setdefaulttimeout(90)

class ProcessMsg(threading.Thread):
    __slots__ = ['parent', 'uid', 'isStop', 'isPause', 'name', 'conn']
    
    def __init__(self, parent, uid):
        threading.Thread.__init__(self) 
        self.parent  = parent
        self.uid     = uid
        self.conn    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.isStop  = False
        self.isPause = False
        self.name    = 'ElastosServer'
        self.conn.connect(('127.0.0.1', UtilFunc.getWebServerPort()))
        thread.start_new_thread(self.listening, ())
        
    def send(self, body):
        try:
            self.conn.send(body)
        except Exception, e:
            Log.exception('[%s]Request Cherrypy Except! Reason[%s]'%(self.name,e))
            self.proException()
                
    def pause(self):
        self.isPause = True
        Log.info('[%s]Response[%s] Pause!'%(self.name,self.uid))
        
    def resume(self):
        self.isPause = False
        Log.info('[%s]Response[%s] Resume!'%(self.name,self.uid))
        
    def proException(self):
        self.parent.send({'connection':self.uid,'error':0x4001}, ERROR)
        self.stop()
            
    def stop(self):
        self.isStop = True
        if self.conn: self.conn.close()
        
    def listening(self):
        while not self.isStop:
            try:
                while self.isPause:
                    time.sleep(0.5)
                ret = self.conn.recv(DATABUF)
                if not ret:
                    break
                self.parent.send(ret, RESPONSE, self.uid)
            except socket.timeout, e:
                continue
            except Exception, e:
                Log.exception('[%s]Response Except! Reason[%s]'%(self.name,e))
                self.proException()
        if self.parent.threads.has_key(self.uid):
            pro = self.parent.threads.pop(self.uid)
            pro.stop()
        Log.info('[%s]RequestThread completed!'%self.uid)

class HubTunnel(NetTunnel):
    
    def __init__(self):
        NetTunnel.__init__(self)
        self.name       = 'Hub'
        self.magicCode  = HMCODE
        self.pingCode   = HPING
        self.retdict    = {}
        self.relay      = RelayTunnel(self)
        self.methods    = {RELAYPREPARE   :'_onRelayPrepare',
                           MESSAGE        :'_onMessage',
                           SHORTURLACK    :'_onShortUrlAck',
                           PINGACK        :'_onPingAck',
                           VERIFYTOKENACK :'_onVerifyTokenAck',
                           ACCESSGRANTED  :'_onAccessGranted',
                           ACCESSREVOKED  :'_onAccessRevoked'}
        
    def _onConnectDown(self):
        if self._stop: return
        self.stop()
        Command.ledFlash(3)
        Log.info('[Hub]Server Connection Disconnect! ReConnect 10s Later!')
        time.sleep(10)
        thread.start_new_thread(self.connect,(self.host, self.port, {}, True))
        
    def _onAccept(self,msg):
        Log.info('[Hub]Server Connect Successfull!')
        natPorts = [{'name':s.get('name'),'port':s.get('port'),'natPort':''} for s in UtilFunc.getAccessServices()]
        self.updateAccessPoints('',natPorts)
        
        #self.receive(RELAYPREPARE, json.dumps({'token':'43rdew534fg45','service':'534fg45',
        #                           'server':'192.168.3.162', 'port':18080}))
        #time.sleep(10)
        #self.relay.send({'connection':'ijkuy8hhyv','error':0x4001}, ERROR)
        #self.send({'server':'testr1.paopaoyun.com','reason':1,'retry':True,'service':u'Elastos Server'}, RELAYDISCONNECT)
        
    def _onLine(self, params):
        services = [{'name':s.get('name'),'port':s.get('port'),'protocol':'TCP'} for s in UtilFunc.getAccessServices()]
        return {'deviceId':UtilFunc.getSN(),'deviceType':UtilFunc.getDeviceType(),'hardwareVersion':PopoConfig.Hardware,
               'softwareVersion':PopoConfig.VersionInfo,'systemVersion': UtilFunc.getSystemVersion(),
               'system':'Linux/PopoBox','services':services}
        
    def updateAccessPoints(self, natIp='', natPorts=[]):
        services = []
        for subserver in natPorts:
            name = subserver.get('name','')
            localPort = subserver.get('port','')
            natPort = subserver.get('natPort','')
            temp_dict = {'name':name,'port':localPort,'natPort':natPort}
            if not self.relay.isStop():
                temp_dict['relay'] = {'server':self.relay.getRelayHost(),'port':self.relay.getRelayPort()}
            services.append(temp_dict)
        msg = {'natIp':natIp, 'localIp':UtilFunc.getLocalIp(),'services':services}
        self.send(msg, ACCESSPOINTS)
        
    def _onRelayPrepare(self, msg):
        (host,port,token,service) = self.parseData(msg, ('server','port','token','service'))
        if self.relay.isStop():
            self.relay.service = service
            ret = self.relay.connect(host, port, {'token':token,'service':service,'deviceId':UtilFunc.getSN()})
            if not ret:
                self.send({'service':service,'errorCode':self.relay.errCode}, RELAYERROR)
                return
        self.send({'port':self.relay.getRelayPort(),'server':host,'service':service}, RELAYREADY)
    
    def _onMessage(self, msg):
        (clientMsg,) = self.parseData(msg, ('message',))
        command = clientMsg.get('command','')
        if command == 'UNBIND':
            ProfileFunc.clearLibraryDB()
            os._exit(0)
            
        elif command == 'RESTART':
            Log.info('[Hub]PopoBox ReStart!')
            os._exit(0)
    
    def _onShortUrlAck(self, msg):
        (shareId,) = self.parseData(msg, ('shareId',))
        if not shareId: return 
        self.retdict[shareId] = self.parseData(msg)
        
    def _onVerifyTokenAck(self, msg):
        (token,valid) = self.parseData(msg, ('token','valid'))
        if not token: return 
        self.retdict[token] = self.parseData(msg)
            
    def _onAccessGranted(self, msg):
        (token,clientId,expire) = self.parseData(msg, ('token','clientId','expire'))
        if not token or not clientId: return
        WebFunc.addToken(clientId, token, expire)
        
    def _onAccessRevoked(self, msg):
        (tokens,) = self.parseData(msg, ('tokens',))
        if not tokens: return 
        WebFunc.revokToken(tokens)           

class RelayTunnel(NetTunnel):
    __slots__ = ['message', 'threads', '_port', 'magicCode', 'pingCode', 'service', 'name', 'methods']
    
    def __init__(self, message):
        NetTunnel.__init__(self)
        self.message   = message
        self.name      = 'Relay'
        self.threads   = {}
        self.host      = ''
        self.clientPort= 0
        self.magicCode = RMCODE
        self.pingCode  = RPING
        self.service   = None
        self.methods   = {REQUEST  :'_onRequest',
                          PAUSE    :'_onPause',
                          RESUME   :'_onResume',
                          STOP     :'_onStop',
                          CLOSE    :'_onClose',
                          RPINGACK :'_onPingAck'}
    
    def _onConnectDown(self):
        if self.isStop(): return
        self.disConnect()
        Command.ledFlash(3)
        self.message.send({'server':self.host,'reason':1,'retry':True,'service':self.service}, RELAYDISCONNECT)
        
    def _onAccept(self,msg):
        (self.clientPort,) = self.parseData(msg,('port',))
        Log.info('[Relay]RelayServer Connect Successfull! ClientPort: [%s]'%self.clientPort)
    
    def _onLine(self, params):
        return {'deviceId':UtilFunc.getSN(), 'token':params.get('token'), 'service':params.get('service')}
       
    def _onRequest(self, msg):
        (reqId, bodyData) = struct.unpack(FORMAT_Q+FORMAT_S%(len(msg) - UIDLEN), msg)
        if self.threads.has_key(reqId):
            self.threads[reqId].send(bodyData)
        else:   
            pro = ProcessMsg(self,reqId)
            self.threads[reqId] = pro
            pro.start()
            pro.send(bodyData)
            
    def _onPause(self, msg):
        (reqId,) = self.parseData(msg, ('connection',))
        if self.threads.has_key(reqId):
            self.threads[reqId].pause()
            
    def _onResume(self, msg):
        (reqId,) = self.parseData(msg, ('connection',))
        if self.threads.has_key(reqId):
            self.threads[reqId].resume()
            
    def _onStop(self, msg):
        (reqId,reason) = self.parseData(msg, ('connection','error'))
        self.stopRequestThread(reqId) 
        Log.info('Request[%s] Stoped! Reason[%s]'%(reqId,reason))
        
    def _onClose(self, msg):
        self.disConnect()
        Log.info('[Relay]RelayServer DisConnect Successfull!')
        self.message.send({'server':self.host,'reason':0,'retry':False,'service':self.service}, RELAYDISCONNECT)
            
    def getRelayPort(self):
        return self.clientPort
    
    def getRelayHost(self):
        return self.host
    
    def stopRequestThread(self, uid=None):
        if uid:
            uid_list = [uid]
        else:
            uid_list = self.threads.keys()  
            
        for uid in uid_list:
            if self.threads.has_key(uid):
                pro = self.threads.pop(uid)
                pro.stop()
                Log.info('[Relay]RequestThread [%s] Stoped!'%uid)

    def disConnect(self): 
        self.stop()
        self.clientPort = 0
        self.stopRequestThread() 

     