# -*- coding: utf-8 -*-

import os
import sqlite3
import threading
import Log
import Command
import UtilFunc
import ProfileFunc

TB_CACHE  = 'fileCache'
TB_FOLDER = 'folders'
TB_TAGS   = 'tags'
TB_SHARES = 'shares'
_Mutex    = threading.Lock()


def dict_factory(cursor, row):  
    d = {}  
    for idx, col in enumerate(cursor.description):  
        d[col[0]] = row[idx]  
    return d 

def getDBConnection():
    dbPath = ProfileFunc.getUserDBPath()
    if not dbPath: return None
    try:
        db_connect = sqlite3.connect(os.path.join(dbPath, 'es_base.db'))
    except Exception, e:
        Log.error("ConnectDB Error : %e"%e)
        return None
    return db_connect

def execSql(sqlStr, values=None):
    conn = getDBConnection()
    if not sqlStr or not conn: return None
    
    global _Mutex
    onlyUpdate = False
    sqlStrSmall = sqlStr.lower()
    if not sqlStrSmall.startswith('select'):
        onlyUpdate = True
        _Mutex.acquire()
    
    if not onlyUpdate:
        conn.row_factory = sqlite3.Row
        
    conn.text_factory = str
    cur = conn.cursor()
    ret = True
    try:
        if values:
            cur.execute(sqlStr, values)
        else:
            cur.execute(sqlStr)
    
        if onlyUpdate:
            conn.commit()
        else:
            ret = cur.fetchall()
            
    except Exception, e:
        if 'no such table: fileCache' in e: createDBTables()
        Log.exception('_execSql Error:[%s], Reason:[%s]'%(sqlStr, e))
        ret = False
        
    cur.close()
    conn.close()
    if onlyUpdate: _Mutex.release()
    return ret

def createDBTables(conn = None):
    if not conn: conn = getDBConnection()
    if not conn: return None
    conn.execute("CREATE TABLE IF NOT EXISTS folders(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, partpath TEXT,\
                 path TEXT, scanning INTEGER, needScan INTEGER, UNIQUE(path))")
    
    conn.execute("CREATE TABLE IF NOT EXISTS fileCache(id INTEGER PRIMARY KEY AUTOINCREMENT, \
                fileType TEXT, url TEXT, folder TEXT, name TEXT, remarks TEXT,lastModify INTEGER, \
                contentLength INTEGER, groupTime TEXT, UNIQUE(url))")
    
    conn.execute("CREATE INDEX IF NOT EXISTS fileCache_fileType_url_groupTime ON fileCache(fileType,url,groupTime)")
    
    conn.execute("CREATE TABLE IF NOT EXISTS tags(id INTEGER PRIMARY \
                KEY AUTOINCREMENT, fileType TEXT, url TEXT, tag TEXT, UNIQUE(url, tag))")
    
    conn.execute("CREATE TABLE IF NOT EXISTS shares(id INTEGER PRIMARY KEY AUTOINCREMENT, shareId TEXT, location TEXT, \
                url TEXT, name TEXT, contentType TEXT, isFolder INTEGER, extractionCode TEXT, validity INTEGER, \
                contentLength INTEGER, lastModify INTEGER)")
    
    conn.execute("CREATE INDEX IF NOT EXISTS shares_shareId ON shares (shareId)")
    
    conn.execute("CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, section TEXT)")
    
    conn.commit()
    conn.close()
        
def dropDBTable(table):
    conn = getDBConnection()
    if not conn: return None
    conn.execute('DROP TABLE IF EXISTS %s'%table)
    conn.commit()
    conn.close()
        
def initDBTables():
    dropDBTable(TB_CACHE)
    createDBTables()
    if UtilFunc.isPCMode() and not tableSelect(TB_FOLDER):
        path = ProfileFunc.GetPictureFolder()
        tableInsert(TB_FOLDER, ['type', 'partpath', 'path', 'scanning', 'needScan'], ['all', UtilFunc.getDiskPath(path), path,'0','1'])
        
    for disk in ProfileFunc.GetBoxDisks():
        did, fs, name = Command.getDiskInfo(disk)
        path = UtilFunc.getDiskPath(disk,True)
        ProfileFunc._fileService.diskInfo[path] = {'id':did,'fs':fs,'name':name}
    
    
def execFileCacheTags(sql=None, side=True, type='picture', params={}):
    offset = int(params.get('offset',0))
    limit = int(params.get('limit',-1))
    order = params.get('order',None)
    sqlStr = 'SELECT a.*, b.[group_concat(tag)] as tag FROM fileCache a LEFT JOIN\
              (SELECT url, group_concat(tag) FROM tags GROUP BY url) b \
              ON a.url = b.url WHERE a.fileType = "%s"'%type
    if not side: 
        sqlStr = 'SELECT * FROM tags a LEFT JOIN fileCache b ON a.url = b.url \
                  WHERE a.fileType = "%s"'%type
    if sql: sqlStr += sql
    if order: sqlStr += ' ORDER BY %s'%order
    if limit > 0: 
        sqlStr += ' LIMIT %d'%limit
        if offset != 0: sqlStr += ' OFFSET %d'%offset
        
    return execSql(sqlStr)
     
def tableSelect(table, keys=[], wheres='', whereTrue=None, params={}):
    offset = int(params.get('offset',0))
    limit = int(params.get('limit',-1))
    order = params.get('order',None)
    if not keys: keys = '*'
    sqlStr = 'SELECT %s FROM %s '%(','.join(keys), table)
    if wheres: sqlStr += 'WHERE ' + wheres
    if order: sqlStr += ' ORDER BY %s'%order
    if limit > 0: 
        sqlStr += ' LIMIT %d'%limit
        if offset != 0: sqlStr += ' OFFSET %d'%offset
            
    return execSql(sqlStr, whereTrue)

def tableInsert(table, keys, values=(), isReplace=False):
    sqlStr = 'INSERT'
    if isReplace: sqlStr = 'REPLACE'
    sqlStr += ' into %s(%s) values(%s)'%(table, ','.join(keys), ','.join(['?' for i in xrange(0, len(keys))]))
    return execSql(sqlStr, values)

def tableRemove(table, wheres, whereTrue = None):
    sqlStr = 'DELETE FROM %s '%table
    if wheres: sqlStr += 'WHERE ' + wheres
    return execSql(sqlStr, whereTrue) 
  
    
if __name__ == '__main__':
    initDBTables()
    