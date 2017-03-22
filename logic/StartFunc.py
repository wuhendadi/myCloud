# -*- coding: utf-8 -*-

import sys
import os
import threading
import cherrypy
import time
import thread
import uuid
import Log
import TaskManager
import UtilFunc
import PopoConfig
#import ProfileFunc
import SqliteFunc
import Command
import WebFunc
import Status

from FileService import Files
from Batch import Batch
from Search import Search
from SystemService import Version, Storages, System, ESLog
from ShareService import Share, GuestShare
from PhotoService import Photos
from MediaService import Music, Video
from Backup import Backup
from portal.portal import portal
from cherrypy import _cpserver
from cherrypy import _cpwsgi_server
from WebServer import WebServer
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.version import __version__
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp



class StoppableThread(threading.Thread):     
    """Thread class with a stop() method. The thread itself has to check     regularly for the stopped() condition."""      
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(StoppableThread, self).__init__(target=target, args=args)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

def upnploop(upnpObj, messageChannel):
    Log.info("StartUPNP......")
    UPNP_Lock = os.path.join(UtilFunc.getLockDataPath(), 'Upnp.lock')
    if not os.path.exists(UPNP_Lock):
        while True:
            f = open(UPNP_Lock, "w")
            f.close()
            needPorts = UtilFunc.getAccessServices()
            natPorts = upnpObj.getUPNPInfo(needPorts)
            Log.info('UPNPInfo: NatIP[%s], NatPort[%s]'%(upnpObj.natip, natPorts))
            os.remove(UPNP_Lock)
            if not natPorts:
                natPorts = [{'name':port.get('name'),'port':port.get('port'),'natPort':''} for port in needPorts]
            messageChannel.updateAccessPoints(upnpObj.natip, natPorts)
            Log.info("Send UpnpInfo Complite!")
            time.sleep(90)
    else:
        os.remove(UPNP_Lock)

cherryThread = None
startedConnect = False

def _getMountConfig(authOn=True, sessionsOn=False):
    return {'request.dispatch'             : cherrypy.dispatch.MethodDispatcher(),
            'tools.auth.on'                : authOn,
            'tools.sessions.on'            : sessionsOn,
            'tools.json_in.on'             : True,
            'tools.json_in.force'          : False,
            'tools.caching.on'             : False,
            'tools.trailing_slash.on'      : False,
            'tools.gzip.on'                : True,
            'tools.gzip.mime_types'        : "['text/*', 'application/json']",
            'tools.staticdir.on'           : True,
            'tools.staticdir.dir'          : UtilFunc.module_path(),
            'tools.staticdir.content_types': {'rss' : 'application/xml',
                                              'atom': 'application/atom+xml'}
            }
    
def mountService(service, apiname):
    cherrypy.tree.mount(service, apiname, config={'/': _getMountConfig()})
    if hasattr(service, 'checkdisks') and service.checkdisks == False:
        WebFunc.NO_CHECKDISK_API.append(apiname)
        
def Cherry():
    Log.info('######################Start Cherrypy!########################')
    cherrypy.config.update({'environment'                  : 'production',
                            'engine.autoreload_on'         : False,
                            'checker.on'                   : False,
                            'server.socket_host'           : '0.0.0.0',
                            'server.socket_port'           : UtilFunc.getWebServerPort(),
                            'server.thread_pool'           : 6,
                            'server.thread_pool_max'       : 10,
                            'server.max_request_body_size' : sys.maxint,
                            'log.screen'                   : True,
                           })
    
    services = {'/storages':Storages(), '/system':System(), '/version':Version(), 
                '/files':Files(), '/share':Share(), '/search':Search(), '/logs':ESLog(),
                '/batch':Batch(), '/photos':Photos(), '/music':Music(), 
                '/video':Video(), '/backup':Backup()}
    
    if not UtilFunc.isPCMode(): 
        from Apps.AppCtrl import AppCtrl
        services['/app'] = AppCtrl()
    
    for server in services.keys():
        mountService(services[server], "/api" + server)

    Log.info('Mount APIServices Complete!')
    
    cherrypy.tree.mount(portal(), '/', 
                            config={'/': {'tools.auth.on'         : False,
                                          'tools.staticdir.on'    : True,
                                          'tools.staticdir.dir'   : UtilFunc.module_path(),
                                         },
                                    })
    Log.info('Mount Portal Service Complete!')
    
    cherrypy.tree.mount(GuestShare(), '/share', config={'/': _getMountConfig(False)}) 
    Log.info('Mount GuestShare Service Complete!')
    
    try:
        server2 = _cpwsgi_server.CPWSGIServer()
        server2.bind_addr = ('0.0.0.0', 1984)
        adapter2 = _cpserver.ServerAdapter(cherrypy.engine, server2, server2.bind_addr)
        adapter2.subscribe()
        cherrypy.tree.graft(WebServer().my_crazy_app, "/web")
    
        syncdir = os.path.join(os.getcwd(),"sync")
        if not os.path.exists(syncdir):
            os.mkdir(syncdir)
        config = {"mount_path"      :"/syncservice",
                  "provider_mapping":{"webdav":syncdir},
                  "user_mapping"    :{},
                  "verbose"         :2,
                  "dir_browser"     :{
                                      "enable"          : True,
                                      "response_trailer": "",
                                      "davmount"        : False,
                                      "msmount"         : False
                                      }
                }
        cherrypy.tree.graft(WsgiDAVApp(config),"/syncservice")
        Log.info('Start WsgiDAV Complete!')
    except Exception, e:
        Log.info('WsgiDAV Start Failed! Reason[%s]'%e)

    cherrypy.engine.start()
    Log.info('CherryService Started!')
    cherrypy.engine.block()

def scanDisks(parent):
    #ProfileFunc.initDB()
    SqliteFunc.initDBTables()
    try:
        if UtilFunc.isWindowsSystem():
            import Win32FolderMoniter
            parent.folderMoniter = Win32FolderMoniter.FolderMoniter()
        elif UtilFunc.isDarwinSystem():
            import DarwinFolderMoniter
            parent.folderMoniter = DarwinFolderMoniter.FolderMoniter()
        elif PopoConfig.PlatformInfo == 'Box':
            import BoxFolderMoniter
            if PopoConfig.BoardSys == 'android':
                parent.folderMoniter = BoxFolderMoniter.usbhostMoniter()
            else:
                parent.folderMoniter = BoxFolderMoniter.FolderMoniter()
        elif PopoConfig.PlatformInfo == 'Linux':
            import LinuxFolderMoniter
            parent.folderMoniter = LinuxFolderMoniter.FolderMoniter()
    
        parent.folderMoniter.start()
    except Exception,e:
        Log.exception('FolderMoniter Init Failed! Reason[%s]'%e)
    parent.scanFolderMoniter.start()

def action(server):
    cherryThread = StoppableThread(target=Cherry, )                                                                                                                                                                                                                                                                                                       
    cherryThread.start()
#     keyfile = os.path.join(os.path.dirname(__file__),'boxclient.p12')
#     certfile = os.path.join(os.path.dirname(__file__),'ElastosRootCA.pem')
#     thread.start_new_thread(server.hubTunnel.connect,(PopoConfig.ServerHost, PopoConfig.ServerPort, {}, True, keyfile, certfile))
    if UtilFunc.isLinuxSystem() and UtilFunc.toBoolean(PopoConfig.ViaEcs):
        from Sitelib import ecs
        server.ecsModule = ecs.ecsModule() 
        thread.start_new_thread(server.ecsModule.start, ())
        #thread.start_new_thread(Status.Status, (server, server.upnpObj,))
    else:
        if UtilFunc.isWindowsSystem():
            from Sitelib import upnp
            server.upnpObj = upnp.UpupPunch(sn=UtilFunc.getSN())
            thread.start_new_thread(upnploop,(server.upnpObj, server.hubTunnel))
        thread.start_new_thread(server.hubTunnel.connect,(PopoConfig.ServerHost, PopoConfig.ServerPort, {}, True))
        
    thread.start_new_thread(Status.broadcast, ())
    if PopoConfig.ScanFolder: scanDisks(server)
