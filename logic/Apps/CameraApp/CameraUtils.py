# -*- coding: utf-8 -*-
import os
import UtilFunc

import sqlite3
import threading
import time
import uuid
import PopoConfig
import Log
import thumbnail

_Mutex = threading.Lock()
CameraPath = None

def setCameraPath(path):
    global CameraPath
    CameraPath = path

def getCameraPath():
    return CameraPath

def getWindowsDBPath():
    pass

def makeDirs(path):
    if os.path.exists(path):
        return
    if UtilFunc.isLinuxSystem():
        disk = UtilFunc.getDiskPath(path)
        if not disk and path.startswith('/mnt'):
            return
    os.makedirs(path)

def getCameraDB():
    if UtilFunc.isLinuxSystem():
        cameraPath = getCameraPath()
        path = UtilFunc.getDiskPath(cameraPath)
        if not path or not os.path.exists(path):
            Log.error("getDBConnect Failed! path[%s]"%path)
            return False
    path = os.path.join(path, '.cameraApp')
    if not os.path.exists(path):
        makeDirs(path)
    if not path: return None
    return sqlite3.connect(os.path.join(path, 'camera.db'))

def getDBConnect(path):
    path = UtilFunc.getDiskPath(path)
    if not path or not os.path.exists(path):
        Log.error("getDBConnect Failed! path[%s]"%path)
        return False
    path = os.path.join(path, '.cameraApp')
    dbPath = os.path.join(path, 'camera.db')
    try:
        connect = sqlite3.connect(dbPath)
    except Exception, e:
#        Log.error("ConnectSubLibraryDB Error! Reason:[%s]"%e)
        print "ConnectSubLibraryDB Error! Reason:[%s]"%e
        return None
    return connect

def initCameraDB():
    if UtilFunc.isLinuxSystem():
        cameraPath = getCameraPath()
        path = UtilFunc.getDiskPath(cameraPath)
        if not path or not os.path.exists(path):
            Log.error("initCameraDB Failed! path[%s]"%path)
            return
    else:
        path = None
    path = os.path.join(path, '.cameraApp')
    db_path = os.path.join(path, 'camera.db').replace("\\", '/')
    journal_path = db_path.replace('camera.db','camera.db-journal')
    try:
        if os.path.exists(journal_path):
            os.remove(journal_path)
        if os.path.exists(db_path):
            os.remove(db_path)          
    except Exception, e:
        Log.error("Reset SublibraryDb Failed! Reason:[%s]"%e)
        os.rename(path, path + str(time.time()).split(".")[0])
    if not os.path.exists(path):
        makeDirs(path)
        
    conn = sqlite3.connect(os.path.join(path, 'camera.db'))
    if not conn: return
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS fileCache(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                fileType TEXT, url TEXT, folder TEXT, uid TEXT, name TEXT, minHash TEXT, maxHash TEXT, lastModify INTEGER, \
                contentLength INTEGER, idCode TEXT, month TEXT, week TEXT, isExist INTEGER, UNIQUE(url))")
        conn.commit()
    except:
        Log.debug('Init Camera DB failed!!!')
        return
    conn.close()

def buildCameraScanFolder():
    pass

def addCameraFileCache(path):
    try:
        if getCameraPath() not in path:
            return
        
        if not os.path.exists(path) or os.path.isdir(path):
            return

        name = os.path.basename(path)
        for fileType in PopoConfig.filters.keys():
            if UtilFunc.matchFilter(name, PopoConfig.filters[fileType]):
                if fileType == 'video' or fileType == 'picture':
                    ret = []
                    ret = getDBDataByURL(path)
                    if not ret:
                        minHash, maxHash = getThumbHash(path)
                        insertCameraDB(fileType, path, minHash, maxHash, 1)
                    else:
                        updateCameraDB(1, path, False)
#                    thumbnail.getOrCreateThumb(path, savePath, fileType, None)
                    thumbnail.getThumbNailImage(path)
                return
    except Exception,e:
        Log.exception('addCameraFileCache[%s] Failed!'%path)


def addToCameraDB(camera_folder_path):
    try:        
        if not camera_folder_path or not os.path.exists(camera_folder_path):
            return
        
        for sub_file in os.listdir(camera_folder_path):
            sub_path = os.path.join(camera_folder_path, sub_file)
            if os.path.isdir(sub_path):
                addToCameraDB(sub_path)
            else:
                if UtilFunc.isHiddenFile(sub_path) or sub_file[:5] == ".popo" or sub_file[:4] == ".tmp":
                        continue
                addCameraFileCache(sub_path)
    except:
         Log.exception('addToCameraDB[%s] Failed!'%camera_folder_path)


def insertCameraDB(fileType, filePath, minHash, maxHash, isExist):
    modifyTime = os.path.getmtime(filePath)
    group = time.strftime('%Y-%m', time.localtime(modifyTime))
    yeaWeek = time.strftime("%Y-%W",time.localtime(modifyTime))
    size = os.path.getsize(filePath)
    idCode = UtilFunc.getMd5(filePath + str(modifyTime) + str(size))
    uid = filePath.split('/')[5]
    SqlStr = 'replace into fileCache(fileType, url, folder, uid, name, lastModify, contentLength, minHash\
    , maxHash, idCode,month, week, isExist) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)'
    execCameraSql(SqlStr,(fileType, filePath, os.path.dirname(filePath), \
            uid, os.path.basename(filePath), modifyTime*1000, size, minHash, maxHash, idCode, group, yeaWeek, isExist))

def execCameraSql(sqlStr, whereTube):
    return _execSql(getCameraDB(), sqlStr, whereTube)

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
        #Log.exception('_execSql Error:[%s], Reason:[%s]'%(sqlStr, e))
        print 'camera _execSql Error:[%s], Reason:[%s]'%(sqlStr, e)
        ret = False
        
    cur.close()
    conn.close()
    _Mutex.release()
    return ret


def updateCameraDB(isExist, filePath, update_all=False):
    if update_all:
        sqlStr = "update fileCache set isExist=?"
        whereTube = (isExist, )
    else:
        sqlStr = "update fileCache set isExist=? where url like ?"
        whereTube = (isExist, filePath)
        
    execCameraSql(sqlStr, whereTube)
    

def delCameraDBWithUrl(filePath):
    if not filePath:
        return
    ret = execCameraSql("select * from fileCache where url like ?", (filePath, ))
    if not ret:
        return
    sqlStr = "delete from fileCache where url like ?"
    whereTube = (filePath, )
    execCameraSql(sqlStr, whereTube)

def delCameraDBWithIsExist():
    sqlStr = "delete from fileCache where isExist=0"
    execCameraSql(sqlStr, None)

def getDBDataByURL(path):
    if not os.path.exists(path):
        return None
    sqlStr = "select * from fileCache where url like ?"
    whereTube = (path, )
    return execCameraSql(sqlStr, whereTube)

def getDBDataByFolder(folder_path):
    if not os.path.exists(folder_path):
        return None
    sqlStr = "select * from fileCache where folder like ?"
    whereTube = (folder_path, )
    return execCameraSql(sqlStr, whereTube)

def getAllDBData():
    sqlStr = "select * from fileCache"
    
    return execCameraSql(sqlStr, None)

def getCameraDBHash():
    ret = []
    minHashs = execCameraSql('select minHash from fileCache where fileType = "picture" or fileType = "video"', None)
    for min_info in minHashs:
        hash = min_info['minHash']
        ret.append(hash)
    maxHashs = execCameraSql('select maxHash from fileCache where fileType = "picture" or fileType = "video"', None)
    for max_info in maxHashs:
        hash = max_info['maxHash']
        ret.append(hash)
    
    return ret

def getThumbHash(filePath, size=170):
    filePath = filePath.replace('\\', '/')
    
    if not os.path.exists(filePath):
        return (None, None)
    
    if UtilFunc.matchFilter(os.path.basename(filePath), PopoConfig.filters['picture']) or UtilFunc.matchFilter(os.path.basename(filePath), PopoConfig.filters['video']):
        minhash = UtilFunc.getMd5Name(filePath, PopoConfig.MinWidth, PopoConfig.MinHeight)
        maxhash = UtilFunc.getMd5Name(filePath, PopoConfig.MaxWidth, PopoConfig.MaxHeight)
    else:
        return (None, None)
    return (minhash, maxhash)

#if __name__ == "__main__":
##    initCameraDB()
##    insertCameraDB("video", "D://123.mp4", "minHash", "masHash", 1)
##    insertCameraDB("video", "D://2.mp4", "minHash", "masHash", 1)
##    insertCameraDB("video", "D://3.mp4", "minHash", "masHash", 1)
##    insertCameraDB("video", "D://4.mp4", "minHash", "masHash", 1)
##    insertCameraDB("video", "D://5.mp4", "minHash", "masHash", 1)
##    updateCameraDB(0, "D://4.mp4", False)
##    filePath = "D://5.mp4"
##    delCameraDBWithUrl(filePath)
##    delNotExist()
##    print getDBDataByURL("D://5.mp4")
##    updateCameraDB(0, None, True)
#    addCameraFileCache("D://3.mp4")
#    pass