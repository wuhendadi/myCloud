# -*- coding: utf-8 -*-
#author: ZJW

import os
import cherrypy
import ConfigParser
import WebFunc
import ProfileFunc
import shutil
import Backup
from PopoConfig import VersionInfo
import cgi
import zipfile
import VCardParser
import tempfile
import Log
import UtilFunc
from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from Sitelib import ReverseProxy
from FileService import createFile,Files
from cherrypy.lib import static

file_dir = ''
env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__))))

def noBodyProcess():
    """Sets cherrypy.request.process_request_body = False, giving
    us direct control of the file upload destination. By default
    cherrypy loads it to memory, we are directing it to disk."""
    cherrypy.request.process_request_body = False

cherrypy.tools.noBodyProcess = cherrypy.Tool('before_request_body', noBodyProcess)

class myFieldStorage(cgi.FieldStorage):
    """Our version uses a named temporary file instead of the default
    non-named file; keeping it visibile (named), allows us to create a
    2nd link after the upload is done, thus avoiding the overhead of
    making a copy to the destination filename."""
    
    def make_file(self, binary=None):
        return tempfile.NamedTemporaryFile()


class portal:
    
    def __init__(self):
        self.name     = 'ESPortal'
        self.cfpath   = os.path.join(os.path.dirname(os.path.abspath(__file__)),'reverseProxy.conf')
        self.proxyMap = {}
        self._run()
        
    def mount(self, path, serverURL, rewriteHost = True):
        self.proxyMap[path] = serverURL
        ReverseProxy.proxyPass(path, serverURL, rewriteHost)
        
    def _run(self):
        cf = ConfigParser.ConfigParser()
        cf.read(self.cfpath)
        for section in cf.sections():
            local = cf.get(section, 'local')
            host = cf.get(section, 'host')
            port = cf.get(section, 'port')
            self.mount(local, 'http://%s:%s'%(host,port))
    
    @cherrypy.expose 
    def index(self, *arg, **params):
        try:
            if params.get('storages'):
                storages = params.get('storages')
            elif params.get('disk') and not UtilFunc.isWindowsSystem():
                storages = params.get('disk')
                storages = ProfileFunc.get_name_label(storages)
            else:
                storages = ProfileFunc.GetBoxDisks(False)[0]
            
            global file_dir
            file_dir = storages
            tmpl = env.get_template('popoCloud.html')
            s_stores = []
            list_files = []
            extInfo = {}
            extInfo['limit'] = 1000 
            extInfo = UtilFunc.getOptParamsInfo(extInfo)
    
            if os.path.exists(storages):
                for file_info in UtilFunc.getFileList(storages, extInfo):
                    list_files.append({"path":file_info.get('url').split("/")[-1],"size":file_info.get("contentLength"),"modify":file_info.get("lastModify")})

            
            if UtilFunc.isWindowsSystem():
                if ProfileFunc.GetBoxDisks(False):
                    names = [u'我的磁盘一']
            else:
                for s_store in ProfileFunc.GetBoxDisks(False):
                    s_stores.append(ProfileFunc.get_label_name(s_store))
                    names = s_stores
            return tmpl.render(names=names, list_files = list_files)

        except Exception,e:
            Log.exception('index Failed! Reason[%s]'%e)

    @cherrypy.expose 
    def documentpage(self, *arg, **params):
        global file_dir
        return self.index(storages=file_dir)

    @cherrypy.expose 
    def createfile(self, *arg, **params):
        global file_dir
        if not file_dir:
            file_dir = ProfileFunc.GetBoxDisks(False)[0]
        if params.get("docname"):
            file_path = os.path.join(file_dir,params.get("docname"))
            createFile(file_path,False,{'size':1})
        return self.index(storages=file_dir)

    @cherrypy.expose 
    def application(self, *arg, **params):
        tmp = env.get_template('application.html')
        return tmp.render()

    @cherrypy.expose 
    def cloudset(self, *arg, **params):
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo)
 
    @cherrypy.expose 
    @cherrypy.tools.noBodyProcess()
    def post_file(self, *arg, **params):
        cherrypy.response.timeout = 3600
        global file_dir
        store_path = file_dir 

        lcHDRS = {}
        for key, val in cherrypy.request.headers.iteritems():
            lcHDRS[key.lower()] = val
        
        
        formFields = myFieldStorage(fp=cherrypy.request.rfile,
                                    headers=lcHDRS,
                                    environ={'REQUEST_METHOD':'POST'},
                                    keep_blank_values=True)
        
       
        if formFields.has_key("theFile"):
            theFile = formFields["theFile"]
            file_name = theFile.filename
        else:
            return "erro"
        if not theFile.file:
            return "erro"
        name  = os.path.join(store_path, file_name)
        with open(name, 'wb') as f:
            f.write(theFile.file.read())
        return self.index(storages=file_dir)
    
    @cherrypy.expose 
    def download_file(self, *arg, **params):
        global file_dir
        zip_file = os.path.join(ProfileFunc.GetBoxDisks(False)[0], 'zip_file.zip')
        if os.path.exists(zip_file):
            os.remove(zip_file)
        file_names= params.get('names')
        file_names = file_names.split(',')
        file_paths = []
        for file_name in file_names:
            file_paths.append(os.path.join(file_dir, file_name))

        try:
            zip = zipfile.ZipFile(zip_file,'w',zipfile.ZIP_DEFLATED)
            for filename in file_paths:
                zip.write(filename)
            zip.close()
        except Exception,e:
            Log.exception('rename Failed! Reason[%s]'%e)
        return static.serve_file(zip_file, "application/x-download", "attachment", os.path.basename(zip_file))
    download_file.exposed = True

    @cherrypy.expose 
    def delete_file(self, *arg, **params):
        global file_dir
        file_names= params.get('names')
        file_names = file_names.split(',')
        file_paths = []
        try:
            for file_name in file_names:
                file_paths.append(os.path.join(file_dir, file_name))
            for file_name in file_paths:
                if not os.path.isdir(file_name):
                    os.remove(file_name)
                else:
                    shutil.rmtree(file_name)

        except Exception,e:
            Log.exception('rename Failed! Reason[%s]'%e)
        return self.index(storages=file_dir)
           
    @cherrypy.expose 
    def rename_file(self, *arg, **params):
        global file_dir
        new_name = params.get("name")
        old_name = params.get("old_name")
        try:
            base_path = file_dir 
            old_name = os.path.join(base_path, old_name)
            new_name = os.path.join(base_path, new_name)
            os.rename(old_name, new_name)
        except Exception,e:
            Log.exception('rename Failed! Reason[%s]'%e)
        return self.index(storages=file_dir)

    @cherrypy.expose 
    def nextpage(self, *arg, **params):
        global file_dir
        page = params.get("page",0)
        return self.index(storages=file_dir, page=page)
    

    @cherrypy.expose 
    def next_dir(self, *arg, **params):
        global file_dir
        file_dir =os.path.join(file_dir,params.get("nextdir")) 
        if not os.path.isdir(file_dir):
            file_dir = os.path.dirname(file_dir)
        return self.index(storages=file_dir)
       
    @cherrypy.expose 
    def back(self, *arg, **params):
        global file_dir
        if file_dir not in ProfileFunc.GetBoxDisks(False):
            file_dir = os.path.dirname(file_dir)
        return self.index(storages=file_dir)
        
    @cherrypy.expose 
    def calllist(self, *arg, **params):
        page_num = params.get('page_num',0)
        page_num = int(page_num)
        backup = Backup.Backup()
        result = []
        rets = []
        backup._getContactFolderInfo(result, filePath=Backup.getContactBackupDir())
        for info in result:
            path = info.get('url')
            path = UtilFunc.formatPath(path)
            rets = rets + VCardParser.vcf_parser(path)
        max_num = len(rets)/20 - 1
        ret = rets[page_num*20:page_num*20+20]
        tmp = env.get_template('listcall.html')
        return tmp.render(ret=ret, max_num=range(max_num), cur_page_num=page_num, max_page=max_num)

    @cherrypy.expose 
    def unbindthunder(self, *arg, **params):
        try:
            from Apps.thunderManager import thunderManager
            manage = thunderManager()
            manage.unbind()
        except Exception,e:
            Log.exception('rename Failed! Reason[%s]'%e)
        return self.application()

    @cherrypy.expose 
    def unbindaccount(self, *arg, **params):
        return self.cloudset()

    @cherrypy.expose 
    def opennetsurf(self, *arg, **params):
        try:
            from Apps.openvpnApp import NetSurf
            netsurf = NetSurf.NetSurf()
            netsurf.PUT(intent="status ", value=True)
        except Exception,e:
            Log.exception('opennetsurf Failed! Reason[%s]'%e)
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo, check_surf=True)

    @cherrypy.expose 
    def shutdownnetsurf(self, *arg, **params):
        try:
            from Apps.openvpnApp import NetSurf
            netsurf = NetSurf.NetSurf()
            netsurf.PUT(intent="status ", value=False)
        except Exception,e:
            Log.exception('shutdownnetsurf Failed! Reason[%s]'%e)
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo, check_surf=False)

    @cherrypy.expose 
    def openshadowsockets(self, *arg, **params):
        try:
            from Apps.shadowsocksApp import shadowsocks
            shadow_socket = shadowsocks.ShadowSocks()
            shadow_socket.PUT(intent="status ", value=True)
        except Exception,e:
            Log.exception('operatesockets Failed! Reason[%s]'%e)
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo, check=True)

    @cherrypy.expose 
    def shutdownsockets(self, *arg, **params):
        try:
            from Apps.shadowsocksApp import shadowsocks
            shadow_socket = shadowsocks.ShadowSocks()
            shadow_socket.PUT(intent="status ", value=False)
        except Exception,e:
            Log.exception('shutdownsockets Failed! Reason[%s]'%e)
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo, check=False)

    @cherrypy.expose 
    def opennet(self, *arg, **params):
        netopen=params.get("netopen",'true')
        if netopen == 'true':
            netopen = 'true'
        else:
            netopen = 'false'
        tmp = env.get_template('cloudset.html')
        return tmp.render(version=VersionInfo, net_open=netopen)
