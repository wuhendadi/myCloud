# -*- coding: utf-8 -*-

import platform
import md5
import string
import os
import sys
import locale
import time
import fnmatch
import traceback
import socket
import types
import threading
import cherrypy
import uuid
import base64
import statvfs
import eyed3
import re
import random
import json
import mimetypes
import ProfileFunc
import SqliteFunc
import WebFunc
import Log
import PostStatic as static
import zipfile

from PopoConfig import *
#from pyDes import triple_des, CBC, PAD_PKCS5

attrs = {'title'    :"TIT2",
         'artist'   :"TPE1",
         'composer' :"TPE2",
         'album'    :"TALB",
         'track'    :"TRCK"}

if ServerHost == 'cs.elastos.com':
    DEFAULTCODE = 'big5'
else:
    DEFAULTCODE = 'cp936'    


def we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""
    return hasattr(sys, "frozen")

def module_path():
    """ This will get us the program's directory,
    even if we are frozen using py2exe"""

    if we_are_frozen() and isWindowsSystem():
        return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
    
    if isDarwinSystem():
        return os.getcwd()

    return os.path.dirname(unicode(os.path.realpath(__file__), sys.getfilesystemencoding()))

def getLogger():
    return Log.getLogger()

def isPCMode():
    return 'Windows' in platform.system() or 'Darwin' in platform.system()

def isWindowsSystem():
    return 'Windows' in platform.system()

def isLinuxSystem():
    return 'Linux' in platform.system()

def isDarwinSystem():
    return 'Darwin' in platform.system()

def getSpecialFolder(csidl):
    from win32com.shell import shell
    pidl = shell.SHGetSpecialFolderLocation(0, csidl)
    folderPath = shell.SHGetPathFromIDList(pidl).decode(locale.getdefaultlocale()[1])
    return folderPath

def getRelativePath(path, folderPathLen):
    relPath = path[folderPathLen+1:]
    relPath = relPath.replace('\\', '/')
    return relPath

def moveFolder(old_path, new_path):
    for folder in os.listdir(old_path):
        sub_folder = os.path.join(old_path, folder)
        if folder in os.listdir(new_path):
            moveFolder(sub_folder, os.path.join(new_path, folder))
        else:
            os.system("mv '%s' '%s'"%(sub_folder, new_path))
    if os.path.exists(old_path): os.rmdir(old_path)

def isHiddenFile(path):
    if isLinuxSystem() or isDarwinSystem():
        if os.path.basename(path)[:1] == ".":
            return True
    else:
        import win32file
        f_type = win32file.GetFileAttributesW(path)
        if f_type&2 != 0:
            return True
    return False

def hideFile(filePath):
    if isWindowsSystem():
        cmd = 'attrib +h "' + filePath +'"'
        cmd = cmd.encode(locale.getdefaultlocale()[1])
        os.popen(cmd).close()
        time.sleep(1)
    
def removeDir(dirPath):
    if not os.path.isdir(dirPath):
        return
    files = os.listdir(dirPath)
    try:
        for file in files:
            filePath = os.path.join(dirPath, file)
            if os.path.isfile(filePath):
                os.remove(filePath)
            elif os.path.isdir(filePath):
                removeDir(filePath)
        os.rmdir(dirPath)
    except Exception, e:
        getLogger().error("removeDir Failed!!![%s]"%e)
        
def makeParentDir(filePath):
    (folderPath, _) = os.path.split(filePath)
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)

def getMd5OfFile(fname):
    if not os.path.exists(fname): return None
    try:
        f = file(fname, 'rb')
        m = md5.new()
        while True:
            d = f.read(16384)
            if not d:
                break
            m.update(d)
        f.close()
        return m.hexdigest()
    except Exception,e:
        getLogger().error('getMd5File Failed! Reason[%s]'%e)
        return None
    
def unZip(base_dir, dest_dir):
    z = zipfile.ZipFile(base_dir)
    for f in z.namelist():
        dest_file = os.path.join(dest_dir, f)
        dest_file = dest_file.replace('\\', '/')
        if dest_file.endswith('/'):
            if not os.path.exists(os.path.dirname(dest_file)):os.makedirs(os.path.dirname(dest_file))
        else:
            if os.path.exists(dest_file): os.remove(dest_file)
            file(dest_file, 'wb').write(z.read(f))
    z.close()
    
def getFileEtag(path):
    if not os.path.exists(path): return None
    st = os.stat(path)
    key = path
    if isLinuxSystem():
        disk = getDiskPath(path)
        if not disk:
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
        fs = ProfileFunc.getMainServer().diskInfo.get(disk,{}).get('fs','')
        if fs == 'fuseblk': key = st.st_ino
            
    name = '%s-%s-%s'%(key,st.st_size,st.st_mtime)
    return md5.md5(repr(name)).hexdigest()

def getMd5Name(filePath, width, height):
    md5_file = getFileEtag(filePath)
    if not md5_file: md5_file = filePath
    name = '%s:%d_%d'%(md5_file, width, height)
    return md5.md5(repr(name)).hexdigest()

def getFileExt(path):
    return os.path.splitext(path)[1][1:].lower()

def get_available_drives():
    import ctypes
    import itertools
    drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    return list(itertools.compress(unicode(string.ascii_uppercase), map(lambda x:ord(x) - ord('0'), bin(drive_bitmask)[:1:-1])))

def encryptDesKey(data):
    return base64.urlsafe_b64encode(data).replace('\n','')
#     import  binascii
#     _des = triple_des(Key_value, CBC, Mode_value, pad=None, padmode=PAD_PKCS5)
#     return  binascii.hexlify(_des.encrypt(str(data)))

def decryptDesKey(code):
    return base64.urlsafe_b64decode(code)
#     import  binascii
#     _des = triple_des(Key_value, CBC, Mode_value, pad=None, padmode=PAD_PKCS5)
#     return _des.decrypt(binascii.unhexlify(code))

def getParentPath(strPath):
    if not strPath :
        return ''

    strLen = len(strPath)
    if strLen == 0:
        return ''
    elif strLen == 1:
        if isSlash(strPath):
            return ''
    elif strLen < 4 and strPath[1] == ':':
        if strLen == 2:
            return ''
        c =  strPath[2]
        if isSlash(c):
            return ''

    lsPath = os.path.split(strPath)
    if lsPath[1] :
        return lsPath[0]

    lsPath = os.path.split(lsPath[0])
    return lsPath[0]

def dictInfoCmp(file1, file2, orderBy):
    if ['isFolder',-1] not in orderBy and ['isFolder',1] not in orderBy:
        orderBy.append(['isFolder',-1])
    for orderItem in orderBy:
        orderItemKey = orderItem[0]
        if orderItemKey not in file1 or orderItemKey not in file2:
            continue

        cmpResult = cmp(file1[orderItemKey], file2[orderItemKey])
        if cmpResult != 0:
            return cmpResult*orderItem[1]
        
    return 0

def getMd5(pwd):
    return md5.md5(md5.md5(pwd).hexdigest()).hexdigest()

def getRemainSpace(filePath):
    if isLinuxSystem():
        disk_space, used_space, capacity = getLinuxDiskInfo(getDiskPath(filePath))
    elif isDarwinSystem():
        disk_space, used_space, capacity = getDarwinDiskInfo(getDiskPath(filePath))
    else:
        disk_space, used_space, capacity = getWindowsDiskInfo(filePath)
    return disk_space, capacity


def getLinuxDiskInfo(path):
    if not os.path.isdir(path): path = os.path.dirname(path)
    if path and os.path.exists(path):
        vfs = os.statvfs(path)
        print vfs[statvfs.F_BSIZE]
        available=vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/1024  
        capacity=vfs[statvfs.F_BLOCKS]*vfs[statvfs.F_BSIZE]/1024
        used = capacity - available
        
        return available, used, capacity
        
    return None,None,None

def getDarwinDiskInfo(path):
    if not os.path.isdir(path): path = os.path.dirname(path)
    if path and os.path.exists(path):
        vfs = os.statvfs(path)
        print vfs[statvfs.F_BSIZE]
        available=vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/(1024 * 1024)  
        capacity=vfs[statvfs.F_BLOCKS]*vfs[statvfs.F_BSIZE]/(1024 * 1024)
        used = capacity - available
        
        return available, used, capacity
        
    return None,None,None

def getWindowsDiskInfo(filePath):
    import win32file
    if not os.path.isdir(filePath): filePath = os.path.dirname(filePath)
    filePath = getShortPath(filePath)
    sectorsPer, bytesPer, numFree, totalNum = win32file.GetDiskFreeSpace(filePath)
    disk_space = (sectorsPer * bytesPer * numFree) / 1024
    max_space = (sectorsPer * bytesPer * totalNum) / 1024
    used_space = max_space - disk_space
    return disk_space, used_space, max_space

def isLowDiskSpace(path, lowspace=MinSpace):
    if not isPCMode():
        diskpath = getDiskPath(path)
        if isLinuxSystem():
            disk_space, used_space, max_space = getLinuxDiskInfo(diskpath)
        elif isDarwinSystem():
            disk_space, used_space, max_space = getDarwinDiskInfo(diskpath)
        if disk_space <= lowspace:
            return True
    return False

def isLinuxDiskReadOnly(path):
    if isLinuxSystem():
        try:
            path = getDiskPath(path)
            if not path: path = ProfileFunc.GetBoxDisks()[0]
            file_path = os.path.join(path, ".popo_ReadOnly")
            file(file_path,"wb").close()
            os.remove(file_path)
        except Exception,e:
            Err_msg = "Check Disk[%s] State Except! Info:[%s]"%(path,e)
            Log.warning(Err_msg)
            #if "[Errno 30] Read-only file system" in Err_msg:
            return True
    return False

def changeMod(path, num):
    if not isLinuxSystem():
        return
    os.system('chmod -R %s %s'%(num,path))
    
def getDefaultPath(path=None):
    if path:
        if not getDiskPath(path):
            return os.path.join(ProfileFunc.GetBoxDisks(False)[0], path[1:] if path.startswith('/') else path)
        return path
    else:
        return ProfileFunc.GetBoxDisks(False)[0]
    
def getAndroidMountPaths(nodeDir, root='/' + MntName):
    paths = []
    baseDir = os.path.join(root, nodeDir)
    if os.path.ismount(baseDir):
        usbParts = [os.path.join(baseDir, a) for a in os.listdir(baseDir) if os.path.ismount(os.path.join(baseDir, a))]
        if usbParts:
            paths += usbParts
        else:
            paths.append(baseDir)
            
    return paths

def getDiskPath(path, flag = False):
    if isWindowsSystem() and os.path.exists(path):
        args = path.split(':')
        if args: return args[0] + ':/'
        else: return None
    elif isDarwinSystem() and os.path.exists(path):
        if flag: return getAppDataFolder()
        return '/' + path.split('/')[1]
    if path:
        disks = ProfileFunc.GetBoxDisks()
        if disks: 
            if isLinuxSystem():
                disks.append("/mnt/popoCloud")
            for disk in disks:
                disk = disk.replace('\\','/')
                if disk in path: return disk
    return None

def getSiteRoot(path):
    if isWindowsSystem():
        return path.split(':')[1].replace('\\','/').replace('//','/')
    elif isDarwinSystem():
        return '/' + '/'.join(path.split('/')[2:])
    else:
        path = re.sub(r'/mnt/disk\d{1,2}/part\d{1,2}', '', path.replace('/mnt/popoCloud/', '/'))
        if not path: path = '/'
        return path.replace('\\','/').replace('//','/')

#-------------------------------------------------------------
def makeDirs(path):
    if os.path.exists(path):
        return
    if isLinuxSystem():
        disk = getDiskPath(path)
        if not disk and path.startswith('/mnt'):
            raise cherrypy.HTTPError(465, 'Not Exist Disk')
    os.makedirs(path)

def getAppDataFolder():
    if isWindowsSystem():
        from win32com.shell import shellcon
        path = getSpecialFolder(shellcon.CSIDL_APPDATA)
    elif isLinuxSystem():
        return App_path
    else:
        path = os.path.expanduser('~')
    return path

def getPopoCloudAppDataPath():
    path = os.path.join(getAppDataFolder(), 'popoCloud')
    makeDirs(path)
    return path

def getLocalPath(path):
    if isPCMode():
        return getPopoCloudAppDataPath()
    makeDirs(path)
    return path
    
def getBoxUpLockPath():
    return getLocalPath(Upl_path)    
    
def getBoxLogPath():
    return getLocalPath(Log_path)

def getLockDataPath():
    return getLocalPath(Lock_path)

#-----------------------------------------------------------------------------
def isSlash(c):
    return c == '/' or c == '\\' or c == '/mnt/disks' or c == '/mnt' or c == '/mnt/sata'

#0:equal
#1:path1 is sub folder of path2
#-1:path2 is sub folder of path1
#2: unrelated
def comparePath(path1, path2):
    if not path1 or not path1:
        return 2

    path1Len =  len(path1)
    path2Len =  len(path2)

    if path1Len > path2Len:
        longPath = path1
        shortPath = path2
        cmpFator  = 1
    else:
        longPath = path2
        shortPath = path1
        cmpFator  = -1

    shortPathLen = len(shortPath)
    longPathLen = len(longPath)
    i = 0
    j = 0
    while i < shortPathLen and j < longPathLen:
        c1 = shortPath[i]
        c2 = longPath[j]
        if isSlash(c1):
            if not isSlash(c2):
                return 2
            while i < shortPathLen and isSlash(shortPath[i]):
                i += 1
            while j < longPathLen and isSlash(longPath[j]):
                j += 1
        else:
            if c1 != c2:
                if i == shortPathLen:
                    return cmpFator
                else:
                    return 2
            i += 1
            j += 1

    if i == shortPathLen:
        if j == longPathLen:
            return 0
        while j < longPathLen:
            if not isSlash(longPath[j]):
                return cmpFator
            j += 1
        return 0
    else:
        return 2
    
def formatPath(arg):
    if not arg: return None
    if not isWindowsSystem(): 
        if not isinstance(arg, types.ListType) and not isinstance(arg, types.TupleType):
            return arg
        arg = list(arg)
        curr = getRealPathByName(arg[0])
        if curr: arg[0] = curr[1:]
        path = '/' + '/'.join(arg)
    else:
        if not isinstance(arg, types.ListType) and not isinstance(arg, types.TupleType) and arg.startswith('/'):
            arg = arg[1:].split('/')
        if len(arg) == 1 and len(arg[0]) != 1 : return arg[0]
        path = arg[0].upper() + ':/' + '/'.join(arg[1:])
        
    return path

def getRealPathByName(name):
    num = 1
    for disk in ProfileFunc.GetBoxDisks():
        diskname = u'Storage' + str(num)
        if diskname in name:
            return disk
        num += 1
    return None

def getRetRange(files, order='', offset=0, limit=-1):
    if len(order) > 0:
        files.sort(lambda x,y: dictInfoCmp(x, y, order))    
        
    if limit >= 0:
        files = files[offset:(limit + offset)]
    else:
        files = files[offset:]

def getFileList(folder, extInfo={}):
    files = []
    order = extInfo.get('orderBy', [])
    limit = int(extInfo.get('limit',-1))
    offset = int(extInfo.get('offset', 0))
    if not isinstance(folder, types.ListType): folder = [folder]
    for _folder in folder: 
        for filename in os.listdir(_folder):
    #         try:
    #             if isWindowsSystem(): filename = filename.decode('gbk')
    #         except:
    #             pass
            fileFullPath = os.path.join(_folder, filename)
            if isHiddenFile(fileFullPath) or filename[:5] == ".popo":
                continue
            fileInfo = getFileInfo(fileFullPath, extInfo)
            if not fileInfo :
                Log.debug("get %s file info failed"%repr(fileFullPath))
                continue
            files.append(fileInfo)
    
    if len(order) > 0:
        files.sort(lambda x,y: dictInfoCmp(x, y, order))    
        
    if limit >= 0:
        files = files[offset:(limit + offset)]
    else:
        files = files[offset:]

    return files
    
def getFileInfo(fileFullPath, extInfo={}, flag=False):
    fileShortPath = getShortPath(fileFullPath)
    if not IsMediaInserted(fileShortPath):
        return None

    if isShorcut(fileShortPath):
        fileFullPath = getShortcutRealPath(fileShortPath)
        fileShortPath = getShortPath(fileFullPath)
    
    fileInfo = formatFileInfo(fileFullPath, flag)
    if matchFilter(os.path.basename(fileFullPath), filters['picture']):
        if not os.path.isfile(fileShortPath): 
            fileInfo['isadd'] = ProfileFunc.isMediaFolder(fileShortPath)
        elif not isPicturePath(fileShortPath):
            return None

    return fileInfo

def walkFolder(folder, type = 'picture', params = {}):
    folders, files = [], []
    for filename in os.listdir(folder):
        if isWindowsSystem(): filename = filename.decode('gbk')
        subfolder = os.path.join(folder,filename).replace('\\','/').replace('//','/')
        if os.path.isdir(subfolder):
            info = {'name':filename,'url':subfolder}
            folders.append(info)      
        else:
            continue
    folder = folder.decode('utf8').replace('\\','/').replace('//','/')
    if type in ['music','video']:
#         sqlStr = 'select * from fileCache where fileType = ? and folder = ?'
#         ret = ProfileFunc.execSubLibrarySqlbyPath(folder, sqlStr, (type,folder,))
        ret = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, [], 'fileType = ? and folder = ?', (type,folder,))   
        files = formatMediaRet(ret, {'order':params.get('order',None)}) 
    elif type == 'picture':
        ret = SqliteFunc.execFileCacheTags(' and a.folder = "%s"'%folder)
        files = formatPhotoRet(ret, {'order':params.get('order',None)})
    
    start = int(params.get('offset',0))
    limit = int(params.get('limit',-1))
    if int(limit) != -1: 
        folders = folders[start:(start + limit)]
        files = files[start:(start + limit)]
    else:
        folders = folders[start:]
        files = files[start:]
    
    return folders, files

def IsSubFolder(longPath, shortPath):
    return comparePath(longPath, shortPath) == 1

def TrimPath(pathStr):
    if not pathStr:
        return None

    pathStrLen = len(pathStr)
    c = None

    while pathStrLen > 0:
        c = pathStr[pathStrLen -1]
        if isSlash(c):
            pathStrLen = pathStrLen -1
        else:
            break

    if pathStrLen < 1:
        return None

    ret = pathStr[0:pathStrLen]
    if c == ':':
        ret += '\\'
    return ret

def isFolderEmpty(path):
    if not path:
        return False
    folder_list = os.listdir(path)
    if not folder_list:
        return True
    return False

def setFileName(filename):
    count = 1
    if not os.path.exists(filename):
        return filename
    name_tuple = os.path.splitext(filename)
    while True:
        new_filename = name_tuple[0] + "(" + str(count) + ")" + name_tuple[1]
        count += 1
        if not os.path.exists(new_filename):
            return new_filename
        
def setFileTime(path, newtime, type='m'):
    if not newtime: return
    try:
        floattime = int(float(newtime))
        if len(str(floattime)) > 10: floattime = int(floattime) / 1000
    except:
        floattime = getFloatTime(newtime)
    try:
        if type == 'm':
            os.utime(path, (int(floattime), int(floattime)))
    except Exception,e:
        Log.exception('SetFiletimes Failed! Reason[%s]'%e)
        raise cherrypy.HTTPError(463, 'Not Permitted')
    
def getUtcTime(seconds=None):
    if not seconds: seconds = time.time()
    if len(str(int(seconds))) > 11: seconds = seconds / 1000
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime(seconds))
    
def getFloatTime(newtime):
    struct_time = tuple(re.findall(r'(\d+)', str(newtime))) + (0,0,0)
    return time.mktime(map(int,struct_time))
        
def formatAutoUploadPath(parentFolder):
    disk = ProfileFunc.GetBoxDisks()
    if not disk: return None
    disk_path = os.path.join(disk[0], "Camera Uploads")
    if not os.path.exists(disk_path): os.mkdir(disk_path)
    parentFolder = parentFolder.replace(parentFolder.split("Camera Uploads")[0], disk[0]+ "/")
    return parentFolder

def StringUrlEncode(str):
    if isinstance(str, unicode):
        str = str.encode('utf8')
    reprStr = repr(str).replace(r'\x', '%')
    return reprStr[1:-1]

def GetModuleHandle(filename=None):
    from ctypes import windll,WinError
    h= windll.kernel32.GetModuleHandleW(filename)
    if not h:
        raise WinError()
    return h

def IsMediaInserted(filePath):
    if not isWindowsSystem():
        return os.path.exists(filePath)

    import win32api
    from ctypes import windll
    if len(filePath) < 1:
        return False

    driveRoot = filePath[0]+':\\'
    oldError = windll.kernel32.SetErrorMode(32769)
    try:
        ret = win32api.GetVolumeInformation(driveRoot)
    except:
        ret = None
    windll.kernel32.SetErrorMode(oldError)

    if ret:
        return True
    else:
        return False

def matchFilter(name, filters):
    try:
        name = name.decode('utf-8').lower()
    except:
        name = name.lower()
    if not isinstance(filters,list):
        filters = filters.split(";")
    for filter in filters:
        filter = filter.lower()
        if len(filter) < 1:
            continue
        if filter.find('*') < 0:
            filter = '*'+ filter + '*'
        if fnmatch.fnmatch(name, filter):
            return True
    return False

def getShortPath(pathStr):
    if not isWindowsSystem():
        return pathStr
    import win32api
    if not os.path.exists(pathStr):
        return pathStr
    try:
        pathStr = win32api.GetShortPathName(pathStr)
    except:
        getLogger().error(traceback.format_exc())
    return pathStr

def isShorcut(filePath):
    if not isWindowsSystem():
        return False
    filePathLen = len(filePath)
    if filePathLen < 5:
        return False
    return filePath[filePathLen-4:].lower() == '.lnk' and os.path.isfile(filePath)

def getShortcutRealPath(filePath):
    try :
        import pythoncom
        from win32com.shell import shell
        pythoncom.CoInitialize()
        shortcut = pythoncom.CoCreateInstance(
                        shell.CLSID_ShellLink, None,
                        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(filePath)
        fileRealPath = shortcut.GetPath(shell.SLGP_SHORTPATH)[0]
        fileRealPath = fileRealPath.decode(locale.getdefaultlocale()[1])
        return fileRealPath
    except :
        getLogger().error(traceback.format_exc())
        return filePath

def isPortFree(port):
    getLogger().info('isPortFree=' + str(port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
    except Exception, e:
        sock.close()
        getLogger().error('isPortFree Port[%s] Failed! Reason[%s]'%(str(port),e))
        return False
    
    sock.close()
    return True

def getFreePort(preferPort):
    port = preferPort
    while True:
        if isPortFree(port):
            return port
        
        if port < 8000:
            port += 8000
        else:
            port += 3

def Now():
    return int(1000 * time.time())

def toBoolean(str):
    if not str:
        return False

    if isinstance(str, types.BooleanType):
        return str

    if isinstance(str, types.StringTypes):
        strLower = str.lower()
        return strLower == 'true' or strLower == '1'

    return False

def toLinuxSlash(pathStr):
    if not pathStr:
        return None
    if isWindowsSystem():
        pathStr = '/' + pathStr.replace(':','')
    return pathStr.replace('\\', '/').replace('//','/')

def strToList(strlist):
    try:
        if not isinstance(strlist, types.ListType):
            strlist = json.loads(strlist)
    except:
        raise cherrypy.HTTPError(460, 'Bad Parameter')
    
    return strlist

#---------------------------------------------------------------------------------------
_programIsRunning = True
_programExitEvent = threading.Event()
def programIsRunning():
    global _programIsRunning
    return _programIsRunning

def exitProgram():
    global _programIsRunning,_programExitEvent
    _programIsRunning = False
    _programExitEvent.set()

def waitProgramExit():
    global _programExitEvent
    _programExitEvent.wait()
    
#-------------------------------------------------------------------------------------    
def getAccessServices():
    needPorts = UpnpPort
    needPorts['Elastos Server'] = getWebServerPort()
    return [{'name':k,'port':v} for (k,v) in needPorts.iteritems()]

def getLocalIp(ifname = 'eth0'):
    try:
        if isWindowsSystem() or isDarwinSystem():
            ip = socket.gethostbyname(socket.gethostname())
        else:
            import fcntl, struct
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            inet = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))
            ip = socket.inet_ntoa(inet[20:24])
        return ip
    except:
        if ifname == 'eth0':                    
            return getLocalIp('wlan0')
        else:
            getLogger().error(traceback.format_exc())
            return '127.0.0.1'

_webServerPort = None
def getWebServerPort():
    global _webServerPort
    if _webServerPort and _webServerPort > 0:
        return _webServerPort

    _webServerPort = getFreePort(8880)
    return _webServerPort

def mergeSubFolder(folders, key = None):
    ret = []
    for folder1 in folders:
        hasIncluded = False
        for folder2 in folders:
            if key:
                folder1Path = folder1[key]
                folder2Path = folder2[key]
            else:
                folder1Path = folder1
                folder2Path = folder2
            if IsSubFolder(folder1Path, folder2Path):
                hasIncluded = True
                break
        if not hasIncluded:
            ret.append(folder1)
    return ret

def orderAndLimit(ret, params):
    orderBy = params.get('order',None)    
    if orderBy:
        cmpInfo = httpArgToCmpInfo(orderBy)
        if len(cmpInfo) > 0 :
            ret.sort(lambda x,y: dictInfoCmp(x, y, cmpInfo))
    start = int(params.get('offset',0))
    limit = int(params.get('limit',-1))       
    if limit > 0:
        return ret[start:(start + limit)]
    else:
        return ret[start:]

def getOptParamsInfo(attr):
    extInfo = {'showHideFile':False, 'showSystemFile':True, 'orderBy':[], 'offset':0,
               'limit':-1, 'recursive':None, 'intent':None, 'filter':None}
    if attr.has_key('showHideFile') and attr['showHideFile'].lower() == 'true':
        extInfo['showHideFile'] = True

    if attr.has_key('showSystemFile') and attr['showSystemFile'].lower() == 'false':
        extInfo['showSystemFile'] = False

    if attr.has_key('orderBy'):
        extInfo['orderBy'] = httpArgToCmpInfo(attr['orderBy'])

    if attr.has_key('offset'):
        extInfo['offset'] = int(attr['offset'])

    if attr.has_key('limit'):
        extInfo['limit'] = int(attr['limit'])
        
    if attr.has_key('recursive'):
        extInfo['recursive'] = attr['recursive']
        
    if attr.has_key('intent'):
        extInfo['intent'] = attr['intent']
    
    if attr.has_key('filter'):
        extInfo['filter'] = attr['filter']
        
    return extInfo

def httpArgToCmpInfo(arg):
    orderItems = arg.split(',')
    ret = []
    for orderItem in orderItems:
        orderItemInfo = []
        orderItemParts = orderItem.split(' ')
        if len(orderItemParts) < 1:
            continue

        orderItemInfo.append(orderItemParts[0])
        if len(orderItemParts) == 2 and orderItemParts[1].lower() == 'desc':
            orderItemInfo.append(-1)
        else:
            orderItemInfo.append(1)
        ret.append(orderItemInfo)
    return ret

def formatFileInfo(fileFullPath, flag=False):
    fileInfo = {}
    fileInfo['url'] = toLinuxSlash(fileFullPath)
    fileInfo['name'] = os.path.basename(fileFullPath)
    try :
        statInfo = os.stat(fileFullPath)

    except Exception, e:
        Log.debug("GetFileInfo[%s] failed! Reason[%s]"%(repr(fileFullPath),e))
        return None

    if statInfo :
        fileInfo['lastModify'] = getUtcTime(statInfo.st_mtime)
        fileInfo['creationTime'] = getUtcTime(statInfo.st_ctime)
    else :
        fileInfo['lastModify'] = 0
        fileInfo['creationTime'] = 0

    if os.path.isfile(fileFullPath):
        fileInfo['isFolder']      = 'False'
        fileInfo['contentLength'] = statInfo.st_size
        fileInfo['contentType']   = getFileExt(fileFullPath)
        fileInfo['ETag']          = getFileEtag(fileFullPath)
        fileInfo['id']            = encryptDesKey(fileFullPath)
        if flag:
            ProfileFunc.addFileCache(fileFullPath)
            ret = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, ['remarks'], 'url = ?', (fileFullPath,))
            if ret:
                fileInfo['remarks'] = ret[0]['remarks']
    else :
        fileInfo['isFolder'] = 'True'
        
    return fileInfo

def formatFilesRet(datas, params):
    ret = []
     
    for fileInfo in iter(datas):
        path = unicode(fileInfo['url'])
        if not os.path.exists(path):
            continue
        ret.append({'id'            :encryptDesKey(path),
                    'url'           :toLinuxSlash(path),
                    'remarks'       :fileInfo['remarks'],
                    'name'          :os.path.basename(path),
                    'lastModify'    :getUtcTime(fileInfo['lastModify']),
                    'creationTime'  :getUtcTime(os.path.getctime(path)),
                    'contentLength' :fileInfo['contentLength'],
                    'contentType'   :getFileExt(path),
                    'ETag'          :getFileEtag(path),
                    'isFolder'      :not os.path.isfile(path),
                   })
            
    return orderAndLimit(ret, params)

def formatPhotoRet(datas, params):
    ret = []
    start = time.time()
    for fileInfo in iter(datas):
        if not os.path.exists(unicode(fileInfo['url'])):
            continue
        path = toLinuxSlash(fileInfo['url'])
        remarks = json.loads(fileInfo['remarks']) 
        tags = fileInfo['tag']
        if not tags: tags = [] 
        else: tags = tags.split(',')
        ret.append({'url'            :path,
                    'thumbnail-small':remarks.get('thumbnail-small',''),
                    'thumbnail-large':remarks.get('thumbnail-large',''),
                    'name'           :fileInfo['name'],
                    'tags'           :tags,
                    'lastModify'     :fileInfo['lastModify'],
                    'contentLength'  :fileInfo['contentLength'],
                    'contentType'    :getFileExt(path)
                    })
    print time.time() - start
    return orderAndLimit(ret, params)

def formatMediaRet(datas, params):
    ret = []
    if not datas: return ret
    for onefile in iter(datas):
        info = {}
        info['url']  = toLinuxSlash(onefile['url'])
        info['name'] = onefile['name']
        info['id']   = encryptDesKey(onefile['url'])
        remarks      = json.loads(onefile['remarks'])
        for (k,v) in remarks.iteritems():
            info[k] = v
        ret.append(info)
    
    return orderAndLimit(ret, params)

def getVideoInfo(path):
    ret = {'length':'','width':'','title':'','height':'','aspectRatio' :'','videoFormat':'','audioFormat':'',\
           'encodedDate':'','thumbnail':''}
    
    if not os.path.exists(path):
        return ret
    if not isWindowsSystem():
        from Sitelib import libandroidmod
        ret = libandroidmod.get_video_details(path)
    
    return ret

def getId3TagInfo(path):
    ret={'genre':'','year':'','title':'','artist':'','composer' :'','album':'','track':'','duration':''}
    try:
        audiofile = eyed3.load(path)
        ret['duration'] = audiofile.info.time_secs
        tag = audiofile.tag
        if tag:
            for (k,v) in attrs.iteritems():
                frame = tag.frame_set[v]
                if frame:
                    value = frame[0].text
                    try:
                        codingStr = value.encode('latin1','ignore').decode(DEFAULTCODE,'ignore')
                    except:
                        codingStr = value
                    if value and not codingStr: codingStr = value
                    ret[k] = codingStr
                else:
                    ret[k] = ''
                    
            if tag.genre:
                ret['genre'] = tag.genre.name
            try:
                if tag.recording_date:
                    ret['year'] = tag.recording_date.year
            except Exception,e:
                Log.exception('Music[%s] get recordingData Failed!'%path)
                ret['year'] = ''
    except Exception, e:
        Log.exception('Music[%s] getId3TagInfo Failed! Reason[%s]'%(path,e))
        
    return ret

def mediaPlay(idCode):
    if not idCode:
        raise cherrypy.HTTPError(460, 'Bad Parameter')
    try:
        path = unicode(decryptDesKey(idCode))
    except:
        raise cherrypy.HTTPError(460, 'Bad Parameter')
    if not os.path.exists(path):
        raise cherrypy.HTTPError(464, 'Not Exists')
    
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    return static.serve_file(path, mime, 'attachment')

#mediaPlay._cp_config = {'response.stream': True}

#----------------------------------------------------------------


def getMac():
    mac = uuid.uuid1().hex[-12:]
    mac = mac.lower()
    return mac

def getSN():
    sn = getMac()
    try:
        if Hardware == "1.0":
            sn = open(Sn_path).read()
            sn = sn[0:16]
        elif Hardware == "1.5":
#             import device
#             sn = device.sn()
            from Sitelib import libandroidmod
            sn = libandroidmod.execute_shell('getprop ro.serialno').strip()
    except Exception,e:
        getLogger().exception('getSerialNo Failed! Reason[%s]'%e)
        
    return sn

def getDeviceType():
    if isLinuxSystem():
        if Hardware == '1.0':
            return 'PopoBox1.0'
        else:
            from Sitelib import libandroidmod
            device = libandroidmod.property_gets('ro.build.product')
            if device: return device
            else: return 'PopoBox1.5'
        
    return 'PC'

def getSystemVersion():
    if not os.path.exists(System_version):
        return "1.5.0"
    else:
        return open(System_version, "r").read().strip()

def getIMGVersion():
    ret = WebFunc.socketSend('127.0.0.1', 8888, 'get-r1s-sys-info')
    if ret: 
        try:
            rets = ret.split(';')
            return {'ver':rets[0],'upgrade':toBoolean(rets[1])}
        except:
            pass
    return {'ver':'unknown','upgrade':False}

def versionCompare(curver, tarver):
    if curver == tarver: return True
    curver, tarver = curver.split('.'), tarver.split('.')
    for i in xrange(min(len(curver),len(tarver))):
        if int(curver[i]) > int(tarver[i]): 
            return True
        elif int(curver[i]) < int(tarver[i]):
            return False
    if len(curver) < len(tarver): return False
    return True

def isPicturePath(path):
    if os.path.isfile(path) and re.match(r'.+\.jpg|.+\.png|.+\.bmp|.+\.gif', str(path).lower()):
        return True
    else:
        return False
    
def getPictureHashPath(hash):
    for disk in ProfileFunc.getAllDisks(): 
        path = os.path.join(disk, ".popoCloud/ThumbImage", hash[:2], hash)
        path = ProfileFunc.slashFormat(path)
        if os.path.exists(path):
            return path
    return None
            
def is_sub_folder(ele_path, scan_list):
    for scan_path in scan_list:
        if len(ele_path.split('/'))> len(scan_path.split('/')) and ProfileFunc.compare_path(ele_path,scan_path):
            return True
    return False

def createShare(path, validity=-1, isPrivate=True):
    isdir = int(os.path.isdir(path))
    if not isdir:
        ext = getFileExt(path)
        size = os.path.getsize(path)
    else:
        ext = ""
        size = 0
    location = path.replace('\\', '/')
    name = os.path.basename(path)
    access = ''.join([str(random.randint(0,9)) for x in xrange(4)]) if isPrivate else ''
    shareId = uuid.uuid4().hex
    url = WebFunc.getShareUrl(shareId, isPrivate, validity)
    if not url: raise cherrypy.HTTPError(462, 'Operation Failed')
    ret = ProfileFunc.addShare(shareId, location, url, name, ext, isdir, access, validity, size)
    if not ret: raise cherrypy.HTTPError(462, 'Operation Failed')
    
    return shareId, access

if __name__ == "__main__":
    s = encryptDesKey("/mnt/disk1/part4/sdfsd/一千年以后.amr")
    print s
    m = decryptDesKey(s)
    print m
    Hardware = '1.5'
    print getSN()
    #[DBUS_SESSION_BUS_ADDRESS]: [unix:abstract=/tmp/dbus-CuEb8jOT06,guid=49d8d5dfa9bddae331a598a8547eb0a1]
