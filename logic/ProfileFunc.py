# -*- coding: utf-8 -*-

import sqlite3
import threading
import time
import re
import json
import tempfile
import UtilFunc
import PopoConfig
import thumbnail
import Log
import Command
import SqliteFunc

from PopoConfig import *
        
_fileService = ''
_curSearchPath = ''
_Mutex = threading.Lock()

def getMainServer():
    return _fileService

def getMsgChannel():
    return _fileService.hubTunnel

def getDiskStatus():
    if hasattr(_fileService,'scanFolderMoniter'):
        return _fileService.scanFolderMoniter.status
    return 0

def getStorageIds():
    return [_fileService.diskInfo.get(path,{}).get('id','') for path in GetBoxDisks()]

def getDiskById(storageId):
    for disk in _fileService.diskInfo.keys():
        if _fileService.diskInfo.get(disk,{}).get('id','') == storageId:
            return disk
    return None

def GetDesktopFolder():
    if UtilFunc.isWindowsSystem():
        from win32com.shell import shellcon
        return UtilFunc.getSpecialFolder(shellcon.CSIDL_DESKTOPDIRECTORY)
    else:
        return os.path.expanduser('~/Desktop')

def GetDocumentFolder():
    if UtilFunc.isWindowsSystem():
        from win32com.shell import shellcon
        return UtilFunc.getSpecialFolder(shellcon.CSIDL_PERSONAL)
    elif UtilFunc.isLinuxSystem():
        return UtilFunc.getBoxLogPath()
    else:
        return os.path.expanduser('~/Document')
    
def isNoFormatDisk(path):
    try:
        diskinfo = os.popen("busybox df '" + str(path) + "'", 'r').readlines()
        if not diskinfo:
            return True
        diskinfo = diskinfo[1].split()
        if diskinfo[5][:5] != "/mnt/" or int(diskinfo[1]) <= 260:
            return True
        return False
    except Exception, e:
        Log.error("isNoFormatDisk Failed! Reason[%s]"%e)
        return False
    
def GetBoxDisks(root=True):
    disks = []
    
    if UtilFunc.isPCMode():
        for disk in SqliteFunc.tableSelect(SqliteFunc.TB_FOLDER, ['path']):
            path = UtilFunc.getDiskPath(unicode(disk['path'])) if root else unicode(disk['path'])
            if not path in disks: 
                disks.append(path)
            
    elif PopoConfig.Hardware == "1.0":
        list_files = os.listdir('/mnt/disks')
        list_files.sort()
        for part in list_files:
            path = os.path.join('/mnt/disks', part)
            if os.path.isdir(path) and not isNoFormatDisk(path):
                disks.append(path)
    elif PopoConfig.BoardSys == 'android':
        for nodeDir in [a for a in os.listdir('/' + PopoConfig.MntName) if a.startswith(PopoConfig.UsbRoot)]:
            disks += UtilFunc.getAndroidMountPaths(nodeDir)
        disks += UtilFunc.getAndroidMountPaths('sata')
        
        return disks
        
    else:
        list_files = os.listdir('/popobox')
        for folder in list_files:
            if "disk" in folder:
                disk_files = os.listdir('/popobox/' + folder)
                for part in disk_files:
                    if "part" in part:
                        path = '/mnt/' + folder + '/' + part
                        disks.append(path)
        disks.sort()
                        
    return disks
 
 
def GetPictureFolder():
    if UtilFunc.isWindowsSystem():
        from win32com.shell import shellcon
        return UtilFunc.getSpecialFolder(shellcon.CSIDL_MYPICTURES).replace('\\', '/')
    elif UtilFunc.isLinuxSystem():
        return '/mnt/disks'
    else:
        path = os.path.expanduser('~/Pictures')
        if not os.path.exists(path):
            path = os.path.expanduser(u'~/图片')
        if not os.path.exists(path):
            path = os.path.expanduser('~')
        return path.encode("utf-8")

def expandPath(path):
    if not path:
        return path
    path = os.path.expanduser(path) 
    path = path.replace('\\', '/')
    if path[0] != '%' or len(path) < 2 :
        return path
    nameEndIndex =  path.find('%', 1)
    if nameEndIndex < 2:
        return path
    name = path[1:nameEndIndex].lower()
    fullPath = None
    if name == 'document':
        fullPath = GetDocumentFolder()
    elif name == 'picture':
        fullPath = GetPictureFolder()
    elif name == 'desktop':
        fullPath = GetDesktopFolder()
    elif name == 'appdata':
        fullPath = UtilFunc.getAppDataFolder()
    elif name == 'temp':
        fullPath = tempfile.gettempdir()

    if not fullPath:
        return path

    fullPath = fullPath.replace('\\', '/')
    nameEndIndex += 1
    if nameEndIndex >= len(path):
        return fullPath
    c = path[nameEndIndex]
    if UtilFunc.isSlash(c):
        nameEndIndex += 1
    return os.path.join(fullPath, path[nameEndIndex:])

def slashFormat(pathStr):
    if not pathStr:
        return None
    pathStr = expandPath(pathStr)

    if '/' == pathStr:
        if PopoConfig.Hardware == "1.0":
            pathStr = u'/mnt/disks'
        elif PopoConfig.Hardware == "1.5":
            pathStr = '/popobox'

    ret = pathStr.replace('\\', '/')
    return ret.strip()

def isPathValid(path):
    disks = GetBoxDisks()
    if not disks:
        return False
    disks.append("/mnt/popoCloud")
    for part in disks:
        if part in path:
            return True
    
    return False
#-------------------------------------------------------------
def getDefaultProfilePath():
    folderPath = os.path.join(UtilFunc.getPopoCloudAppDataPath(), 'profiles')
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        
    return folderPath

def getUser():
    return 'PopoBox'

def getPassword():
    return ''

def getResource():
    return UtilFunc.getSN()

#-------------------------------------------------------------
def createTable(conn, name):
    if name == 'folders':
        conn.execute("CREATE TABLE IF NOT EXISTS folders(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, partpath TEXT,\
                 path TEXT, scanning INTEGER, needScan INTEGER, UNIQUE(path))")
    elif name == 'fileCache':
        conn.execute("CREATE TABLE IF NOT EXISTS fileCache(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                fileType TEXT, url TEXT, folder TEXT, name TEXT, remarks TEXT,lastModify INTEGER, \
                contentLength INTEGER, groupTime TEXT, UNIQUE(url))")
        conn.execute("CREATE INDEX IF NOT EXISTS fileCache_fileType_url_groupTime ON fileCache(fileType,url,groupTime)")
    elif name == 'config':
        conn.execute("CREATE TABLE IF NOT EXISTS mediafolder(id INTEGER \
                PRIMARY KEY AUTOINCREMENT, url TEXT, type TEXT, UNIQUE(url))")
        
        conn.execute("CREATE TABLE IF NOT EXISTS selectfolder(id INTEGER \
                PRIMARY KEY AUTOINCREMENT,  url TEXT, UNIQUE(url))")

        conn.execute("CREATE TABLE IF NOT EXISTS fileCache(id INTEGER PRIMARY \
                KEY AUTOINCREMENT, fileType TEXT, url TEXT, tag TEXT, UNIQUE(url, tag))")
    
    elif name == 'shares':
        conn.execute("CREATE TABLE IF NOT EXISTS shares(id INTEGER PRIMARY KEY AUTOINCREMENT, shareId TEXT, location TEXT, url TEXT, name TEXT, contentType TEXT, isFolder INTEGER, extractionCode TEXT, validity INTEGER, contentLength INTEGER, lastModify INTEGER)")
        conn.execute("CREATE INDEX IF NOT EXISTS shares_shareId ON shares (shareId)")
    elif name == 'settings':
        conn.execute("CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, section TEXT)")
    
    conn.commit()
        
        
# def initDB():
#     try:
#         initLibraryDB()
#         initSettingDB()
#         initSharesDB()
#     except Exception, e:
#         Log.error("InitDb Error : %s"%e)
    
def getUserDBPath():
    dbPath = getDefaultProfilePath()
    if not os.path.exists(dbPath):
        UtilFunc.makeDirs(dbPath)
    return dbPath

def _execSql(conn, sqlStr, whereTube):
    if not sqlStr or not conn: return None
    
    global _Mutex
    _Mutex.acquire()
    onlyUpdate = False
    sqlStrSmall = sqlStr.lower()
    if not sqlStrSmall.startswith('select'):
        onlyUpdate = True
    
    if not onlyUpdate:
        conn.row_factory = sqlite3.Row
        
    conn.text_factory = str
    cur = conn.cursor()
    ret = True
    try:
        if whereTube:
            cur.execute(sqlStr, whereTube)
        else:
            cur.execute(sqlStr)
    
        if onlyUpdate:
            conn.commit()
        else:
            ret = cur.fetchall()
    except Exception, e:
        if 'no such table: fileCache' in e:
            createTable(conn, 'fileCache')
        Log.exception('_execSql Error:[%s], Reason:[%s]'%(sqlStr, e))
        
        ret = False
        
    cur.close()
    conn.close()
    _Mutex.release()
    return ret

#-------------------------------------------------------------
# def initSettingDB():
#     conn = getSettingDB()
#     if not conn: return
#     createTable(conn, 'settings')
#     conn.close()
#     
#     if  UtilFunc.isLinuxSystem():
#         execSettingSql('delete from settings')
#     
# def getSettingDB():
#     dbPath = getUserDBPath()
#     if not dbPath: return None
#     try:
#         connect = sqlite3.connect(os.path.join(dbPath, 'setting.db'))
#     except Exception, e:
#         Log.error("ConnectSettingDB Error! %s"%e)
#         return None
#     return connect
# 
# def execSettingSql(sqlStr, whereTube=None):
#     return _execSql(getSettingDB(), sqlStr, whereTube)
# 
# def getSetting(section, key):
#     try:
#         ret = execSettingSql('select * from settings where section=? and key=?', (section, key))
#         if not ret or len(ret) != 1:
#             return None
#         return ret[0]['value']
#     except:
#         return None
# 
# def setSetting(section, key, value):
#     ret = execSettingSql('select * from settings where section=? and key=?', (section, key))
#     if not ret or len(ret) == 0:
#         execSettingSql('insert into settings(section, key, value) values(?,?,?)', (section, key, value))
#     else:
#         execSettingSql('update settings set value=? where section=? and key=?', (value, section, key))

def _mergeSameFolder(ret, folderPath, dirInfo):
    retDirInfo = None
    for info in ret:
        if info['url'] == folderPath:
            retDirInfo = info
            break

    if retDirInfo:
        if dirInfo['lastModify'] > retDirInfo['lastModify']:
            retDirInfo['name'] = dirInfo['name']
            return
    else:
        ret.append({'url':folderPath, 'name': dirInfo['name'],
                           'lastModify': dirInfo['lastModify']})

           
def getRootFolderInfo():
    rootDirStr = None
    dbInited = False
    
    if  UtilFunc.isLinuxSystem():
        disks = GetBoxDisks()
        rootDirs = []
        drives_count = 0
        for disk in disks:
            name = getMainServer().diskInfo.get(disk,{}).get('name','')
            rootDirs.append({'url': disk, 'name':name, 'lastModify':UtilFunc.Now()})
            
    else:           
        dbInited = True
        rootDirStr = getSetting('system','rootDir')
    
        if not rootDirStr:
            rootDirs = [
                    {'url': expandPath('picture'),'name':'My Picture', 'lastModify':UtilFunc.Now()},
                    {'url': expandPath('document'),'name':'My Documents', 'lastModify':UtilFunc.Now()},
                    ]
            rootDirStr = json.dumps(rootDirs)
            if dbInited:
                setSetting('system','rootDir', rootDirStr)
        else:
            rootDirs = json.loads(rootDirStr)
    return rootDirs

def getRootFolders():
    if UtilFunc.isWindowsSystem():
        import win32con, win32file

    rootDirs = getRootFolderInfo()
    ret = []
    for dirInfo in rootDirs:
        path = dirInfo['url']
        if UtilFunc.isWindowsSystem() and UtilFunc.isSlash(path):
            drivers = UtilFunc.get_available_drives()
            for disk in drivers:
                folderPath = disk + ':/'
                folderName = disk + ':'
                if UtilFunc.isWindowsSystem():
                    dt = win32file.GetDriveType(folderPath)
                    if dt != win32con.DRIVE_FIXED:
                        continue
                _mergeSameFolder(ret, folderPath, {'name':folderName, 'lastModify':dirInfo['lastModify']})
            continue
        folderPath = expandPath(path)
        _mergeSameFolder(ret, folderPath, dirInfo)
    return ret

#-------------------------------------------------------------
def initSharesDB():
    conn = getSharesDB()
    if not conn: return
    createTable(conn, 'shares')
    conn.close()

def execSharesSql(sqlStr, whereTube=None):
    return _execSql(getSharesDB(), sqlStr, whereTube)  

def getSharesDB():
    dbPath = getUserDBPath()
    if not dbPath: return None
    try:
        connect = sqlite3.connect(os.path.join(dbPath, 'shares.db'))
    except Exception, e:
        Log.error("ConnectSharesDB Error! %s"%e)
        return None
    return connect

def clearSharesDB():
    execSharesSql('delete from shares')
    
def isShareIdEnable(id):
    if id: 
        shares = execSharesSql('select * from shares where shareId=?', (id,))
        if len(shares) != 0:
            return True
    return False

_shareMutex = threading.Lock()
def addShare(shareId, location, url, name, ext, isdir, access, validity, size):
    global _shareMutex
    _shareMutex.acquire()
    try:
        location = location.decode('utf-8')
        name = name.decode('utf-8')
    except:
        pass
    #ret = execSharesSql('select * from shares where shareId=?', (shareId,))
    ret = SqliteFunc.tableSelect(SqliteFunc.TB_SHARES, [], 'shareId=?', (shareId,))
    if not ret or len(ret) == 0:
        #ret = execSharesSql('insert into shares(shareId, location, url, name, contentType, isFolder, extractionCode, validity, contentlength, lastModify) values(?,?,?,?,?,?,?,?,?,?)', (shareId, location, url, name, ext, isdir, access, validity, size, UtilFunc.Now()))
        ret = SqliteFunc.tableInsert(SqliteFunc.TB_SHARES, ['shareId', 'location', 'url', 'name', 'contentType', 'isFolder', 'extractionCode', 'validity', 'contentlength', 'lastModify'],\
                                      (shareId, location, url, name, ext, isdir, access, validity, size, UtilFunc.Now(),))  
    else:
        #ret = execSharesSql('update shares set location=?, url=?, name=?, contentType=?, isFolder=?, extractionCode=?, validity=?, contentlength=?, lastModify=? where shareId=?', (location, url, name, ext, isdir, access, validity, size, UtilFunc.Now(), shareId))
        sqlStr = 'update shares set location=?, url=?, name=?, contentType=?, isFolder=?, extractionCode=?, validity=?, contentlength=?, lastModify=? where shareId=?'
        ret = SqliteFunc.execSql(sqlStr, (location, url, name, ext, isdir, access, validity, size, UtilFunc.Now(), shareId,))
    _shareMutex.release()
    return ret
    
#----------------------------------------------------------------------------------------------------------------------------------------------
def getSearchTableName(sid = None ):
    tempStr = sid
    strinfo = re.compile('-')
    strName = strinfo.sub('_', tempStr)
    return strName

def getTempDB():
#     if UtilFunc.isLinuxSystem():
#         diskPath = GetBoxDisks()[0]
#         dbPath = os.path.join(diskPath, '.popoCloud')
#         if not os.path.exists(dbPath):
#             UtilFunc.makeDirs(dbPath)
#     else:
#         dbPath = getUserDBPath()
#     if not dbPath: return None
#     return sqlite3.connect(os.path.join(dbPath, 'search.db'))
    return sqlite3.connect(os.path.join(tempfile.gettempdir(), 'search.db'))

def freeDBMemory():
    conn = getTempDB()
    if not conn: return
    tableCount = getDBTableCount()
    if 0 == tableCount:
        conn.execute("VACUUM")

def getDBTableCount():
    conn = getTempDB()
    if not conn: return
    sqlStr = 'select name from sqlite_master where type=\'table\' order by name'
    cu = conn.cursor()
    cu.execute(sqlStr)
    ret = cu.fetchall()
    tbCount = len(ret) - 1
    conn.commit()
    cu.close()
    conn.close()
    return tbCount

def initSearchDB( id ):
    conn = getTempDB()
    if not conn: return
    freeDBMemory()
    tableName = getSearchTableName(id)
    try:
        sqlStr = 'CREATE TABLE IF NOT EXISTS \'%s\'(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                   url TEXT, name TEXT, isFolder TEXT, contentType TEXT, ETag TEXT, \
                   contentLength TEXT, creationTime TEXT, lastModify TEXT)'%tableName
        conn.execute(sqlStr)
        conn.commit()
    except:
        Log.debug('search failed!!!')
        return
    conn.close()

def addSearchCacheDB( id, path, name, ext, type, size, lastModify ):
    tableName = getSearchTableName(id)
    sqlStr = 'insert into \'%s\'(url, name, isFolder, contentType, ETag, contentLength,\
                creationTime, lastModify) values(?, ?, ?, ?, ?, ?, ?, ?)'%tableName
    whereTube = (path, name, ext, type, size, lastModify)
    ret = execTempDBSql(sqlStr, whereTube)
    if not ret or len(ret) != 1:
        pass
    else:
        Log.debug('add SearchCacheDB failed!!!')

def execInsertSearchDB( id, ret = None ):
    result = ret
    if 0 == len(result): return
    for _ret in result:
        url = _ret.get('url','')
        name = _ret.get('name','')
        isFolder = _ret.get('isFolder','')
        type = _ret.get('contentType','')
        etag = _ret.get('ETag','')
        length = _ret.get('contentLength','')
        creationTime = _ret.get('creationTime','')
        lastModify = _ret.get('lastModify','')
        sqlStr = 'insert into \'%s\'(url, name, isFolder, contentType, ETag, contentLength,\
                        creationTime, lastModify) values(?, ?, ?, ?, ?, ?, ?, ?)'%getSearchTableName(id)
        try:
            execTempDBSql(sqlStr, (url, name, isFolder, type, etag, length, creationTime, lastModify))
        except Exception, e:
            Log.debug('Insert Failed! Reason[%s]'%e)

    
def delSearchCacheDB(id):
    tableName = getSearchTableName(id)
    execTempDBSql('DROP TABLE IF EXISTS \'%s\''%tableName, None)
    freeDBMemory()

def delSearchTBWithId(searchId, endId):
    tableName = getSearchTableName(searchId)
    sqlStr = 'delete from \'%s\''%tableName
    if endId: sqlStr += ' where id <= %d'%endId
    whereTube = None
    ret = execTempDBSql(sqlStr, whereTube)
    if not ret:
        Log.debug('delete data failed!!!')
        
def getSearchCacheDBCount(searchId):
    tableName = getSearchTableName(searchId)
    sqlStr = 'select count(1) as id from \'%s\''%tableName
    conn = getTempDB()
    if not conn: 
        return
    cu = conn.cursor()
    cu.execute(sqlStr)
    ret = cu.fetchone()
    count = ret[0]
    cu.close()
    conn.close()
    return count

def getSearchTBWithId( id, startId, endId):
    tableName = getSearchTableName(id)
    sqlStr = 'select * from \'%s\' where id > %d'%(tableName, startId)
    if endId: sqlStr += ' and id <= %d'%endId      
    ret = execTempDBSql(sqlStr)
    result = []
    for _result in ret:
        result.append({ 'url': _result[1],
                        'name': _result[2],
                        'isFolder': _result[3],
                        'contentType': _result[4],
                        'ETag': _result[5],
                        'contentLength': _result[6],
                        'creationTime':_result[7], 
                        'lastModify':_result[8],
                        })
    return result
    
def execTempDBSql(sqlStr, whereTube = None):
    return _execSql(getTempDB(), sqlStr, whereTube)

#--------------------------------------------------------------------------------------------------
def initTraversalDB(sid=None ):
    conn = getTempDB()
    if not conn: return
    freeDBMemory()
    tableName = getSearchTableName(sid)
    try:
        sqlStr = 'CREATE TABLE IF NOT EXISTS \'%s\'(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                   url TEXT, name TEXT, isFolder TEXT, contentType TEXT, ETag TEXT, \
                   contentLength TEXT, creationTime TEXT, lastModify TEXT)'%tableName
        conn.execute(sqlStr)
        conn.commit()
    except:
        Log.debug('Traversal failed!!!')
        return
    conn.close()

def execInsertTraversalDB( sid=None, ret=None ):
    return execInsertSearchDB(sid, ret)

def delTraversalCacheDB(sid):
    return delSearchCacheDB(sid)

def delTraversalTBWithId(sid, endId):
    return delSearchTBWithId(sid,endId)

def getTraversalCacheDBCount(sid):
    return getSearchCacheDBCount(sid)

def getTraversalTBWithId(sid, startId, endId):
    return getSearchTBWithId(sid, startId, endId)

def execTraversalSql(sqlStr, whereTube = None):
    return _execSql(getTempDB(), sqlStr, whereTube)

#--------------------------------------------------------------------------------------------------

def getAutoUploadPath():
    if UtilFunc.isWindowsSystem():
        from win32com.shell import shellcon
        disk_path = UtilFunc.getSpecialFolder(shellcon.CSIDL_MYPICTURES)
    else:
        if not GetBoxDisks(): return None
        disk_path = GetBoxDisks()[0]
    try:
        upload_path = os.path.join(disk_path, 'Camera Uploads')
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)
        return upload_path
    except Exception,e:
        Log.error(e)
        return None

#--------------------------------------------------------------------------------------------------
#Lib_Dict = {"picture":'*.png;*.gif;*.bmp;*.jpg',
#            "music":"*.mv;*.ogg;*.wav;*.mp3",
#            "video":"*.rm;*.avi;*.mp4;*.mpeg"}
Lib_Dict = {"picture"  :'*.png;*.gif;*.bmp;*.jpg'}
LibName = 'picture'

def getMediaFolder(disk, default = False):
    strSql = 'select * from mediafolder'
    ret = _execSql(getConfDb(disk), strSql, None)
    if ret:
        return [disk + path['url'] for path in ret]
    elif default:
        return [disk]
    else:
        return []

def isMediaFolder(path):
    return True
    scan_paths = getMediaFolder(UtilFunc.getDiskPath(path, True))
    if not scan_paths: return True
    for scan_path in scan_paths:
        if scan_path in path: return True
    return False
    
def getAllMediaFolders():
    ret = execAllScanFolderSql("select url from mediafolder")
    paths = []
    for sub in ret:
        if sub['url'] not in paths: paths.append(sub['url'])
    return paths


# def initLibraryDB():
#     conn = getLibraryDB()
#     if not conn: return
#     if UtilFunc.isLinuxSystem():
#         for disk in GetBoxDisks():
#             addSubLibrary(disk)
#     else:
#         createTable(conn, 'folders')
#         conn.row_factory = sqlite3.Row
#         cur = conn.cursor()
#         ret = execLibrarySql('select * from folders')
#         if not ret:
#             path = GetPictureFolder()
#             cur.execute("insert into folders(type, partpath, path, scanning, needScan) \
#              values(?,?,?,0,1)",('all', UtilFunc.getDiskPath(path), path,))
#             conn.commit()
#             addSubLibrary(path)
#             _fileService.scanFolderMoniter.setMediaFolder([{'folder':path, 'type':'all'}],[])
#         else:
#             for folder in ret:
#                 path = folder['partpath'] 
#                 if not os.path.exists(path):
#                     execLibrarySql('delete from folders where type = ? and path = ?',(folder["type"],path,))
#                     continue
#                 addSubLibrary(folder['path'])
#         cur.execute('update folders set needScan = 1, scanning = 0')
#         conn.commit()
#         cur.close()
#         conn.close()


def clearLibraryDB():
    global _fileService
    ret = execLibrarySql('select * from folders')
    if not ret or len(ret) < 1:
        return None
    
    for folder in ret:
        folderId = int(folder['id'])
        if UtilFunc.isWindowsSystem():
            _fileService.folderMoniter.delFolder(folder['path'])
            
        _fileService.libBuildManager.cancelAllTask(folderId)
        delSubLibrary(folderId)
       
def getLibraryDB():
    dbPath = getUserDBPath()
    if not dbPath: return None
    try:
        db_connect = sqlite3.connect(os.path.join(dbPath, 'es_base.db'))
    except Exception, e:
        Log.error("ConnectDB Error : %e"%e)
        return None
    return db_connect

def execLibrarySql(sqlStr, whereTube=None):
    return _execSql(getLibraryDB(), sqlStr, whereTube)

# def initSubLibraryDB(path):
#     if not os.path.exists(path): return None
#     db_path = os.path.join(path, 'library.db').replace("\\", '/')
#     journal_path = db_path.replace('library.db','library.db-journal')
#     try:
#         if os.path.exists(journal_path):
#             os.remove(journal_path)
#         if os.path.exists(db_path):
#             os.remove(db_path)          
#     except Exception, e:
#         Log.error("Reset SublibraryDb Failed! Reason:[%s]"%e)
#         os.rename(path, path + str(time.time()).split(".")[0])
#     if not os.path.exists(path): os.mkdir(path)
#     dbPath = os.path.join(path, 'library.db')
#     conn = sqlite3.connect(dbPath)
#     if not conn: return
#     try:
#         createTable(conn, 'fileCache')
#     except Exception, e:
#         Log.error("initSubLibraryDB Failed! Reason[%s]"%e)
#     conn.close()

def initMediaFolderDB(path):
    dbpath = os.path.join(path, 'conf.db')
    conn = sqlite3.connect(dbpath)
    if not os.path.exists(path): os.mkdir(path)
    if not conn: return
    try:
        createTable(conn, 'config')
        conn.close()
    except Exception, e:
        Log.error("initMediaFolder Failed! Reason[%s]"%e)

def getSubLibraryPath(folderId):
    ret = execLibrarySql('select * from folders where id=?', (folderId,))
    if not ret or len(ret) != 1:
        return None

    path = ret[0]['partpath']
    path = os.path.join(path, '.popoCloud')
    path = path.replace('\\', '/')
    return path

def getSubLibraryPathbyFile(filePath):
    if filePath.startswith('/mnt/popoCloud'):
        disk = GetBoxDisks()[0]
        return os.path.join(disk,'.popoCloud').replace("\\","/")
    for disk in GetBoxDisks():
        if disk == filePath[:len(disk)]:
            path = os.path.join(disk,'.popoCloud').replace("\\","/")
            return path
    
    return None 
    
# def getSubLibraryDB(path):
#     if not os.path.exists(path):
#         return None
#     dbPath = os.path.join(path, 'library.db')
#     try:
#         connect = sqlite3.connect(dbPath)
#     except Exception, e:
#         Log.error("ConnectSubLibraryDB Error! Reason:[%s]"%e)
#         return None
#     return connect  

def getConfDb(path):
    if not os.path.exists(path):
        return None
    path = os.path.join(path, '.popoCloud').replace("\\",'/')
    dbPath = os.path.join(path, 'conf.db')
    try:
        connect = sqlite3.connect(dbPath)
    except Exception, e:
        Log.error("ConnectScanfolder Error! Reason:[%s]"%e)
        return None
    return connect

def insertToSubLibrary(savePath, fileType, filePath, remarks):
    modifyTime = os.path.getmtime(filePath)
    group = time.strftime('%Y-%m', time.localtime(modifyTime))
    size = os.path.getsize(filePath)
    ret = SqliteFunc.tableInsert(SqliteFunc.TB_CACHE, ['fileType', 'url', 'folder', 'name', 'lastModify', 'contentLength', \
                                'remarks', 'groupTime'], (fileType, filePath.replace('\\','/'), os.path.dirname(filePath), \
                                os.path.basename(filePath), modifyTime, size, remarks, group, ), True)

def execSubLibrarySqlbyPath(path, sqlStr, whereTube=None):
    path = UtilFunc.getDiskPath(path, True)
    if not path or not os.path.exists(path):
        Log.error("execSubLibrarySqlByPath Failed! path[%s]"%path)
        return False
    path = os.path.join(path, '.popoCloud')
    return _execSql(getSubLibraryDB(path), sqlStr, whereTube)

def execConfDbSqlbyPath(path, sqlStr, whereTube=None):
    path = UtilFunc.getDiskPath(path, True)
    if not path or not os.path.exists(path):
        Log.error("execConfDbSqlbyPath Failed! path[%s]"%path)
        return False
    ret = _execSql(getConfDb(path), sqlStr, whereTube)
    return ret

def optionTags(path, tags=[], action='add',fileType='picture'):
#     dbpath = UtilFunc.getDiskPath(path, True)
#     conn = getConfDb(dbpath)
#     cur = conn.cursor()
#     if not tags:
#         cur.execute('delete from fileCache where url = ?', (path,))
#         conn.commit()
#     else:
#         for tag in tags:
#             if action == 'add':
#                 sqlStr = 'replace into fileCache(url, fileType, tag) values(?, ? ,?)'
#             else:
#                 sqlStr = 'delete from fileCache where url = ? and fileType = ? and tag = ?'
#             cur.execute(sqlStr, (path, fileType, tag,))
#             conn.commit()
#     cur.close()
#     conn.close()
    if not tags:
        SqliteFunc.tableRemove('tags', 'url = ?', (path,))
    else:
        for tag in tags:
            if action == 'add':
                sqlStr = 'replace into tags(url, fileType, tag) values(?, ? ,?)'
            else:
                sqlStr = 'delete from tags where url = ? and fileType = ? and tag = ?'
            SqliteFunc.execSql(sqlStr, (path, fileType, tag,))
    

# def execAllDb(sql=None, side=True, type='picture'):
#     data = []
#     for disk in getAllDisks():
#         folder = os.path.join(disk,".popoCloud").replace("\\","/")
#         mainDb = os.path.join(folder, 'library.db')
#         attachDb = os.path.join(folder, 'conf.db')
#         sqlStr = 'select a.*, b.[group_concat(tag)] as tag from fileCache a left join\
#                   (select url, group_concat(tag) from adb.fileCache group by url) b\
#                   on a.url = b.url where a.fileType = "%s"'%type
#         if not side: 
#             mainDb,attachDb = attachDb, mainDb
#             sqlStr = 'select * from fileCache a left join adb.fileCache b on a.url = b.url \
#                       where a.fileType = "%s"'%type
#         if sql: sqlStr += sql
#         try:
#             conn = sqlite3.connect(mainDb)
#             conn.row_factory = sqlite3.Row
#             conn.execute('ATTACH DATABASE "%s" as adb'%attachDb)
#             cur = conn.cursor()
#             cur.execute(sqlStr)
#             ret = cur.fetchall()
#             cur.close()
#             conn.close()
#         except Exception, e:
#             Log.error('execAllDb Error:[%s], Reason:[%s]'%(sqlStr, e))
#             ret = None
#         
#         if ret and isinstance(ret, list): 
#             data += ret
#     
#     return data

def execAllScanFolderSql(sqlStr, whereTube=None):
    data = []
    for disk in GetBoxDisks():
        retSub = _execSql(getConfDb(disk), sqlStr, whereTube)
        if retSub and isinstance(retSub, list): 
            data += retSub
            
    return data

def getAllSetFolders():
    data = []
    for disk in getAllDisks():
        retSub = _execSql(getConfDb(disk), 'select url from selectfolder', None)
        if retSub and isinstance(retSub, list): 
            retSub = [disk + f['url'] for f in retSub]
            data += retSub
            
    return data

def getAllDisks():
    if UtilFunc.isDarwinSystem():
        return [UtilFunc.getAppDataFolder()]
    return GetBoxDisks()

# def getAllLabels(name='picture', tag='tag'):
#     sql = 'select tag, count(*) from (select * from fileCache \
#             where fileType="%s") group by %s'%(name,tag)
#     ret = execAllScanFolderSql(sql)
#     labels = []
#     for sub in ret:
#         if sub['tag'] not in labels: labels.append(sub['tag'])
#     
#     return labels
 
def removeLabels(tag, filetype='picture'):
    return execAllScanFolderSql('delete from fileCache where tag = "%s" and fileType= "%s"'%(tag,filetype))
    
# def addSubLibrary(path):
#     did, fs, name = Command.getDiskInfo(path)
#     path = UtilFunc.getDiskPath(path,True)
#     _fileService.diskInfo[path] = {'id':did,'fs':fs,'name':name}
#     try:
#         path = os.path.join(path, '.popoCloud')
#         if not os.path.exists(path):
#             UtilFunc.makeDirs(path)
#             UtilFunc.hideFile(path)
#         
#         initSubLibraryDB(path)
#         initMediaFolderDB(path)
# 
#     except Exception, e:
#         Log.error("AddSubLibrary Failed! [%s]"%e)
#         return False
                
def delSubLibrary(folderId):
    path = getSubLibraryPath(folderId)
    Log.info("_delSubLibrary [%s]"%path)
    if path:
        db_path = os.path.join(path, 'library.db').replace("\\", '/')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception, e:
                Log.error(e)
    
def getLibraryFolderInfo(ftype = 'all'):    
    ret = SqliteFunc.tableSelect(SqliteFunc.TB_FOLDER, [], 'type=?', (ftype,))
    folders = []
    for folder in ret:
        folders.append({
                        'path': UtilFunc.toLinuxSlash(folder['path']),
                        'folderId':folder['id'],
                        'scanning':folder['scanning'],
                        })
    return folders     

def removeFolderCache(path):
    SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, 'url like ?', (path + '/%',))
    #execSubLibrarySqlbyPath(folderPath, "delete from fileCache where url like ?", (path + '/%',))

def getHashName(path, filePath):
    try:
        ret = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, ['remarks'], 'url=?', (filePath, ))
        hashs = []
        for result in ret:
            remarks = json.loads(result['remarks'])
            if remarks['thumbnail-small'] not in hashs:
                hashs.append(remarks['thumbnail-small'])
                hashs.append(remarks['thumbnail-large'])
        return hashs
    except:
        return None

def delThumbImage(filePath):
    path = getSubLibraryPathbyFile(filePath)
    if not path or not os.path.exists(path):
        return None
    hashName = getHashName(path, filePath)
    if not hashName:
        return
    for _hashName in hashName:
        try:
            savePath = os.path.join(path, "ThumbImage", _hashName[:2]).replace('\\', '/')
            if os.path.exists(savePath):
                os.remove(os.path.join(savePath, _hashName))
                Log.info("Delete ThumbImage : [%s]"%_hashName)
                if not os.listdir(savePath):
                    os.rmdir(savePath)
        except Exception,e:
            Log.error("DelThumbImage Failed! Reason[%s]"%e)
            continue
            
def RefreshPicturesList():
    if UtilFunc.isWindowsSystem():
        from interface import Frame
        if Frame.MainForm.frame:
            Frame.MainForm.frame.ChangePicturesStatus()

def isAllDiskScaned():
    for k in _fileService.diskState.keys():
        if _fileService.diskState[k] == 3:
            return False
    return True

def addFileToDB(filePath, savePath, fileType):
    if UtilFunc.getFileExt(filePath) == 'mp3':
        remarks = json.dumps(UtilFunc.getId3TagInfo(filePath))
    else:
        remarks = '{}'
    insertToSubLibrary(savePath, fileType, filePath, remarks)

def addFileCache(path, scanType= 'all'):
    try:
        if not os.path.exists(path) or os.path.isdir(path):
            return
        name = os.path.basename(path)
        savePath = os.path.join(UtilFunc.getDiskPath(path, True), '.popoCloud')
        scanType = scanType.lower()
        if scanType != 'all' and scanType in PopoConfig.filters.keys():
            fileTypes = [scanType]
        else:
            fileTypes = PopoConfig.filters.keys()
        for fileType in fileTypes:
            if UtilFunc.matchFilter(name, PopoConfig.filters[fileType]):
                if fileType == 'video' or fileType == 'picture':
                    thumbnail.getOrCreateThumb(path, savePath, fileType)
                else:
                    addFileToDB(path, savePath, fileType)
                return
        if scanType == 'all' or scanType == 'other':
            addFileToDB(path, savePath, 'other')
    except Exception, e:
        Log.exception('AddFileCache[%s] Failed!'%path)

def delFileCache(filePath):
    #ret = execSubLibrarySqlbyPath(filePath, 'select * from fileCache where url=?', (filePath,))
    ret = SqliteFunc.tableSelect(SqliteFunc.TB_CACHE, [], 'url = ?', (filePath,))
    if not ret: return None
    
    if len(ret) > 0:
        delThumbImage(filePath)
        #execSubLibrarySqlbyPath(filePath, 'delete from fileCache where url=?', (filePath,))
        SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, 'url = ?', (filePath,))
    else:
        removeFolderCache(filePath)
             
def addToLibrary(path=None, flag=True, type='all', recursive=False):
    mainServer = getMainServer()
    if UtilFunc.isWindowsSystem() and flag:
        folderId = execLibrarySql('select id from folders where path=? ',(path,))[0][0]
        mainServer.folderMoniter.addFolder(path, folderId)
        mainServer.folderMoniter.notifyConfigChanged()
    else:
        path = slashFormat(path)
                
    mainServer.scanFolderMoniter.addFolder(path, type, recursive)
        
def removeFromLibrary(path):
    mainServer = getMainServer() 
    if UtilFunc.isWindowsSystem():
        mainServer.folderMoniter.delFolder(path)
        mainServer.folderMoniter.notifyConfigChanged()   
    
    #execSubLibrarySqlbyPath(path, "delete from fileCache where url like ?", (path+'/%',))
    SqliteFunc.tableRemove(SqliteFunc.TB_CACHE, 'url like ?', (path+'/%',))
    mainServer.scanFolderMoniter.removeFolder(path)
    SqliteFunc.execSql('delete from folders where path = ?',(path,))
    
    
def deleteRootDir(path): 
    if _fileService.diskState.has_key(path):
        del _fileService.diskState[path]
        execLibrarySql('delete from folders where partpath= ?',(path,))
    
    if UtilFunc.isWindowsSystem():
        rootDirs = getRootFolderInfo()
        path = slashFormat(path)
        index = 0
        count = len(rootDirs)
        while index < count:
            dirInfo = rootDirs[index]
            if path == slashFormat(dirInfo['path']):
                break
            index += 1
        if index >= count:
            return 
        del rootDirs[index]
        setSetting('system', 'rootDir', json.dumps(rootDirs))
  
def getFolderIdByPath(filePath):
    if filePath: 
        ret = execLibrarySql('select * from folders')
        for folder in ret:
            path = folder['path'].lower()
            _filePath = filePath[0:len(path)].lower()
            _filePath = _filePath.replace('\\', '/')
            path = path.replace('\\', '/')
            if _filePath == path:
                return folder['id']

    return None
       
#------------------------------------------------------------- 
def getDefaultDisk():
    disk = '/mnt/popoCloud'
    if os.path.exists(disk):
        return disks
    else:
        return None

def getRecordPath():
    disks = GetBoxDisks()
    if not disks:
        return None
    return disks[0]

def compare_path(path1, path2):
    path1_list = path1.split('/')
    path2_list = path2.split('/')
    if len(path2_list) >= len(path1_list):
        return False
    last_path2_list = path2_list[-1]
    if path2 in path1 and last_path2_list == path1_list[len(path2_list) - 1]:
        return True
    else:
        return False

def image_in_path_list(path, path_list):
    for path_ele in path_list:
        if compare_path(path, path_ele):
            return True
    return False

def get_label_name(label_name):
    for ele in getRootFolderInfo():
        if compare_path(label_name, ele.get('url')) or label_name == ele.get('url'):
            return label_name.replace(ele.get('url'),ele.get('name'))

def get_name_label(name):
    for ele in getRootFolderInfo():
        if name == ele.get('name'):
            return ele.get('url')

def dir_info(path):
    fileInfo = {}
    fileInfo['lastModify'] = int(os.path.getmtime(path) * 1000)
    fileInfo['url'] = path
    fileInfo['name'] = get_label_name(path)
    return fileInfo

