# -*- coding: utf-8 -*-
#author:ZJW


import json
#import jks
import ssl
import struct
import time
import socket
import select
import types
import thread
import threading
import UtilFunc
import Log

from constant import *
# from OpenSSL import SSL
# from OpenSSL.crypto import load_pkcs12,FILETYPE_ASN1,load_certificate,load_privatekey
# 
#  
# def jksfile2context(jksfile, passphrase, certfile):
#     keystore = jks.KeyStore.load(jksfile, passphrase)
#     p12 = load_pkcs12(file(certfile, 'rb').read(), passphrase) 
#     trusted_certs = [load_certificate(FILETYPE_ASN1, cert.cert)
#                      for cert in keystore.certs]
#     ctx = SSL.Context(SSL.TLSv1_METHOD)
#     ctx.set_options(SSL.OP_NO_TLSv1)
#     ctx.use_privatekey(p12.get_privatekey())
#     ctx.use_certificate(p12.get_certificate())
#     ctx.check_privatekey()
# #     for ca in p12.get_ca_certificates():
# #         ctx.add_client_ca(ca)
#     for cert in trusted_certs:
#         ctx.get_cert_store().add_cert(cert)
#     return ctx
# 
# def verify_cb(conn, cert, errnum, depth, ok):
#     # This obviously has to be updated
#     print 'Got certificate: %s' % cert.get_subject()
#     return ok

class NetTunnel:
    
    def __init__(self):
        self.name        = 'NetTunnel'
        self._stop       = True
        self.msglist     = []
        self.connectTime = None
        self.pingCode    = HPING
        self.errCode     = TIMEOUT
        self.mutex       = threading.Lock()
        self.methods     = {}
        
    def _onConnectDown(self, retry=True):
        if self._stop: return
        self.stop()
        if retry:
            Log.info('[%s]Server Connection Disconnect! ReTry 10s Later!'%self.name)
            time.sleep(10)
            thread.start_new_thread(self.connect,(self.host, self.port, {}, True))
        
    def _onAccept(self,msg):
        Log.info('[%s]Server Connect Successfull!'%self.name)
    
    def _onPingAck(self, msg):
        self.connectTime = time.time()
        
    def _packMessage(self, body=None, msgType=None, uid=None):
        buf = struct.pack(FORMAT_H, MAGICCODE[self.name])
        if msgType:
            buf += struct.pack(FORMAT_H, msgType)
        if body:
            if not isinstance(body,types.StringType):
                body = json.dumps(body)
            body_length = len(body)
            if uid:
                buf += struct.pack(FORMAT_I, body_length + UIDLEN)
                buf += struct.pack(FORMAT_Q, uid)
            else:
                buf += struct.pack(FORMAT_I, body_length)
                
            buf += struct.pack(FORMAT_S%body_length, body)
        else:
            buf += struct.pack(FORMAT_I, 0)
            
        return buf
    
    def _checkMagicCode(self, msg):
        (code,) = struct.unpack(FORMAT_H, msg[:MAGICLEN])
        if code == self.magicCode:
            return True
        Log.error("[%s]Receive Message Failed! MagicCode Error!"%self.name)
        return False
    
    def _revData(self, length):
        data, buff_len = '', 0
        if length != 0:  
            while buff_len < length:  
                sub_data = self.conn.recv(length - buff_len)
                data += sub_data
                buff_len = len(data)
        return data
    
    def _onLine(self, params):
        return {}
        
    def connect(self, host, port, params={}, retry=False, key=None, cert=None):
        Log.info('[%s]Server Connecting! HOST[%s] PORT[%s]'%(self.name, host, port))
        try:
            self.host, self.port = host, port
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if key and cert:
                self.key, self.cert = key, cert
                p12 = load_pkcs12(file(key, 'rb').read(), 'elastos')
                ctx = SSL.Context(SSL.TLSv1_METHOD)
                ctx.set_verify(SSL.VERIFY_PEER, verify_cb)
                ctx.use_privatekey(p12.get_privatekey())
                ctx.use_certificate(p12.get_certificate())
                ctx.load_verify_locations(self.cert)
#                 ctx = jksfile2context(self.key,'elastos',self.cert)
                self.conn = SSL.Connection(ctx, conn)
                self.conn.set_connect_state()
                self.conn.settimeout(90)
            else:
                self.conn = conn
            self.conn.connect((host, port))
            self.conn.send(self._packMessage(self._onLine(params), CONNECT))
            msg = self.conn.recv(MESSAGEBUF)
            if self._checkMagicCode(msg[:MAGICLEN]):
                (msgType, length) = struct.unpack(FORMAT_R, msg[MAGICLEN:(LENGTH_R+MAGICLEN)])
                if msgType:
                    if msgType == ACCEPT:
                        self.connectTime = time.time()
                        self.host = host
                        thread.start_new_thread(self._listening, ())
                        thread.start_new_thread(self._loop, ())
                        self._stop = False
                        self._onAccept(msg[(LENGTH_R+MAGICLEN):])
                        return True
                    elif msgType == REFUSE:
                        (errCode,info) = self.parseData(msg[(LENGTH_R+MAGICLEN):], ('reason','message'))
                        Log.error('[%s]Connect Refuse! ErrCode[%s] Info[%s]'%(self.name,errCode,info))
                        self.errCode = errCode
                else:
                    Log.error('[%s]Create Connection Failed! Receive Type Error!'%self.name)
            else:
                Log.error('[%s]Create Connection Failed! Receive Message Error!'%self.name)
                
        except Exception,e:
            Log.exception('[%s]Connect Server[%s] Exception[%s]'%(self.name,host,e))

        self._stop = True
        if self.conn: self.conn.close()
        if retry:
            Log.info('[%s]Server Connect Failed! ReTry 10s Later!'%self.name)
            time.sleep(10) 
            self.connect(host, port, params, retry, key, cert)
        return False
    
    def receive(self, msgType, msg):
        Log.info('[%s]Receive Message From Server! msgType:[%s]'%(self.name,msgType))
        try:
            method = self.methods.get(msgType,None)
            if method:
                self.connectTime = time.time()
                exec('self.%s(msg)'%method)     
        except Exception,e:
            Log.exception('[%s]Receive Exception! Reason[%s]'%(self.name,e))

        return
    
    def send(self, msg=None, msgType=None, uid=None):
        if self.isStop(): 
            if msgType in [RPING,HPING]: return
            self.msglist.append({'msg':msg,'type':msgType,'uuid':uid})
            return
        buf = self._packMessage(msg, msgType, uid)
        start, end = 0, len(buf)
        self.mutex.acquire()
        try:
            while start < end:
                length = self.conn.send(buf[start:])
                start += length      
            Log.info('[%s]Send Message To Server! type[%s] time[%s]'%(self.name,msgType, UtilFunc.getUtcTime()))
        except socket.error, e:
            Log.error('[%s]Server Connection Error! Reason[%s]'%(self.name,e))
            self._onConnectDown()
        except Exception, e:
            Log.info('[%s]SendMessage To Server Except! Reason[%s]'%(self.name,e))
        finally:  
            self.mutex.release()    
               
    def stop(self):
        self._stop = True
        if self.conn: self.conn.close()
    
    def isStop(self):
        return self._stop
    
    def parseData(self, msg, keys=[]):
        (msg,) = struct.unpack(FORMAT_S%len(msg), msg)
        bodyData = json.loads(msg)
        if keys:
            ret = []
            for key in keys:
                ret.append(bodyData.get(key,''))
            return tuple(ret)
        else:
            return bodyData
        
    def _listening(self):
        while not self._stop:
            try:  
                Input, Output, Exception=select.select([self.conn,],[],[self.conn,])
                if Exception:
                    for s in Exception:
                        if s == self.conn:
                            Log.exception("Connect[%s] Exception"%s.getpeername())
                            break  
                for indata in Input:  
                    if indata == self.conn:
                        magicData = self._revData(MAGICLEN)
                        if not magicData or not self._checkMagicCode(magicData):
                            continue
                        buf = self._revData(LENGTH_R)
                        (msgType, length) = struct.unpack(FORMAT_R, buf)
                        data = self._revData(length)
                        self.receive(msgType, data)
                        
                for msg in self.msglist:
                    self.send(msg.get('msg',None),msg.get('type',None),msg.get('uuid',None))
                    self.msglist.remove(msg) 
                    
            except socket.error, e:
                Log.exception('Listenning Except! Server[%s], Reason[%s]'%(self.name,e))
                break
            
        if not self._stop:
            self._onConnectDown()
        
    def _loop(self, delay = PINGDELAY):
        start = time.time() 
        while not self._stop:
            if time.time() - start >= delay:
                self.send(None, self.pingCode) 
                start = time.time()
            if time.time() - self.connectTime > CDELAY:
                self._onConnectDown()
            
            time.sleep(0.1)
            
            

        