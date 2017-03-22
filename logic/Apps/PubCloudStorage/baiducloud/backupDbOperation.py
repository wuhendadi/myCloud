import UtilFunc
from ..import utils
import errors
import os
from os.path import isdir, isfile, getsize, join, splitext, exists
import time
import json
from ..import backupDatabase
from functools import wraps
from ..import request
import shelve

logger = UtilFunc.getLogger()

def create_table_for_disk(uuid_table):
    uuid_table_u = unicode(uuid_table)
    connection = backupDatabase.get_connection()

    query = u'''CREATE TABLE  %s (    id              INTEGER PRIMARY KEY,
                                    requestid       TEXT,
                                    path            TEXT,
                                    type            TEXT,
                                    level           INTEGER,
                                    size            INTEGER,
                                    md5             TEXT,
                                    backupat        INTEGER,
                                    baidupcscode    INTEGER,
                                    baidupcsmd5     TEXT,
                                    baidupcsfsid    INTEGER,
                                    baidupcspath    TEXT,
                                    baidupcssize    INTEGER)'''%uuid_table_u
    logger.debug(query)
    res = backupDatabase.execute_sql(connection, query, write=True)

    error_code = res.get(u'error_code', 0)
    if error_code and error_code != errors.DATABASE_TABLE_ALREADY_EXIST:
        logger.debug(u'create table %s failed, error code %d' % (uuid_table_u, error_code))

    connection.close()

def gen_table_tame_from_uuid(uuid_s):
    return u'table_' + unicode(uuid_s)

def query_file_upload_info(req):
    param = req.param
    path = param[u'path']               #path in file system, used to getsize
    path_disk = param[u'path_disk']    #relevant path of file on disk, used as db table primary key
    request_id = param[u'request_id']
    uuid_s = param.get(u'uuid')
    uuid_table = gen_table_tame_from_uuid(uuid_s)
    uuid_table_u = unicode(uuid_table)

    query = u'''select path, backupat, baidupcscode from %s
                where path=(?)
                and requestid=(?)'''%uuid_table_u

    #logger.debug(query)
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, query, (path_disk, request_id))

    error_code = res.get(u'error_code', 0)
    if error_code == errors.DATABASE_TABLE_NOT_EXIST:
        connection.close()
        create_table_for_disk(uuid_table_u)
        return {u'result':0, u'need_update':1}
    elif error_code:
        connection.close()
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    cursor = res.get(u'data')
    data = cursor.fetchall()
    if not data:
        #logger.debug(u'Didnot find record matched with specified path %s'%path_disk)
        res = {u'result':0, u'need_update':1}
    else:
        p = data[0][0]
        backupat = data[0][1]
        baidupcscode = data[0][2]
        #logger.debug(u'%s %d %d'%(p,backupat,baidupcscode))
        if baidupcscode != 0 or os.path.getmtime(path) > backupat:
            #logger.debug(u'Last time backup failed or file modified')
            res = {u'result':0, u'need_update':1}
        else:
            res = {u'result':0, u'need_update':0}
    connection.close()
    return res

def update_file_upload_info(req):
    param = req.param
    path = param.get(u'path')                 #path in file system, used to getsize
    path_disk = param.get(u'path_disk')      #relevant path of file on disk, used as db table primary key
    request_id = param.get(u'request_id')
    uuid_s = param.get(u'uuid')
    uuid_table = gen_table_tame_from_uuid(uuid_s)
    level = utils.getPathArchLevel(path_disk)

    if isdir(path):
        type = u'd'
        size = 0
    else:
        type = u'f'
        size = getsize(path)
    baidupcsmd5 = param.get(u'baidupcsmd5')
    baidupcsfsid = param.get(u'baidupcsfsid',0)
    baidupcspath = param.get(u'baidupcspath')
    baidupcscode = param.get(u'baidupcscode',0)
    baidupcssize = param.get(u'baidupcssize',0)
    backupat = time.time()

    select = u'''select path, backupat, baidupcscode from %s
                            where path=(?)
                            and requestid=(?)'''%uuid_table
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, select, (path_disk, request_id))

    error_code = res.get(u'error_code', 0)
    if error_code == errors.DATABASE_TABLE_NOT_EXIST:
        create_table_for_disk(uuid_table)
    elif error_code:
        connection.close()
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    # if no table found, cursor object will be none here
    cursor = res.get(u'data')
    if not cursor or not cursor.fetchall():
        insert = u'''insert into %s ( id,
                                    requestid,
                                    path,
                                    type,
                                    level,
                                    size,
                                    md5,
                                    backupat,
                                    baidupcscode,
                                    baidupcsmd5,
                                    baidupcsfsid,
                                    baidupcspath,
                                    baidupcssize)
                    values (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
                '''%uuid_table
        logger.debug(insert)
        res = backupDatabase.execute_sql(connection, \
                                     insert, \
                                     (request_id, path_disk, type, level,\
                                        size, baidupcsmd5, backupat, baidupcscode,\
                                        baidupcsmd5, baidupcsfsid, baidupcspath, baidupcssize), \
                                     write=True)
    else:
        update = u'''update %s
                    set backupat=?,baidupcsmd5=?,baidupcsfsid=?,baidupcspath=?, baidupcscode=?, baidupcssize=?
                    where path=(?)
                    and requestid=(?)
                '''%uuid_table
        logger.debug(update)
        res = backupDatabase.execute_sql(connection, update, (backupat,baidupcsmd5, baidupcsfsid, baidupcspath, \
                                                          baidupcscode,baidupcssize,path_disk, request_id))
    connection.close()
    return res

def query_backup_record_contents(req):
    param = req.param
    uuid_s = param.get(u'uuid')
    path = param.get(u'path')
    start = param.get(u'start',0)
    count = param.get(u'count',-1)
    request_id = param.get(u'request_id')
    path_level = utils.getPathArchLevel(path)
    sub_path_level = path_level + 1
    name = param.get(u'name')
    logger.debug(u'Query backup record, path:%s, uuid_s:%s'%(path,uuid_s))
    uuid_table = gen_table_tame_from_uuid(uuid_s)
    local_path_dir = utils.getPopoboxPathFromUuid(uuid_s)

    if not uuid_s or not path:
        return  {u'result':1, u'error_code':errors.INVALID_PARAMS}

    path_patten = unicode(path) + u'%'
    query = u'''select path,type,baidupcscode,baidupcspath,baidupcssize,size from %s
                where path like (?)
                and level=(?)
                and requestid=(?)
                order by path asc
                limit ?,?
            '''%uuid_table
    logger.debug(query)
    logger.debug(u'%s %d'%(path_patten,sub_path_level))

    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, query, (path_patten,sub_path_level,request_id,start,count))
    error_code = res.get(u'error_code', 0)
    if error_code:
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    files = []
    dirs = []
    cursor = res.get(u'data')
    for row in cursor:
        accesss_p = row[0]
        if not local_path_dir:
            local_path = ''
        else:
            local_path = join(local_path_dir, accesss_p.strip(os.sep))
        size = row[4]
        if size == 0:
            size = row[5]
        data_d =dict(local_path=local_path,filetype=row[1],errCode=row[2],remote_path=row[3],size=size)
        if data_d.get(u'filetype') == u'd':
            dirs.append(data_d)
        else:
            files.append(data_d)
    dirs.extend(files)
    res = {u'result':0, u'data':dirs}

    connection.close()
    return res

def delete_backup_records(req):
    param = req.param
    records = param.get(u'records')
    reqids = []
    reqid_uuidtab_map = {}

    for record in records:
        request_id = record.get(u'request_id')
        uuid = record.get(u'uuid')
        uuid_table = gen_table_tame_from_uuid(uuid)

        reqids.append((request_id, ))
        if reqid_uuidtab_map.get(uuid_table) != None:
            reqid_uuidtab_map.get(uuid_table).append((request_id, ))
        else:
            reqid_uuidtab_map.update({uuid_table:[(request_id, )]})

    connection = backupDatabase.get_connection()

    # step1, delete backupRecord first
    delete1 = u'''delete from backupRecords
                where requestid=(?)
            '''
    res = backupDatabase.execute_sql(connection, delete1, reqids, write=True, execute_many=True)

    #step 2, delete records in each table
    for uuid_table in reqid_uuidtab_map:
        delete2 = u'''delete from %s
                    where requestid=(?)
                ''' % uuid_table
        reqid_args = reqid_uuidtab_map.get(uuid_table, [()])
        logger.debug(repr(reqid_args))
        logger.debug(u'delete %s ' % uuid_table)
        res = backupDatabase.execute_sql(connection, delete2, reqid_args, write=True, execute_many=True)
        logger.debug(repr(res))

    connection.close()
    return res

def delete_all_backup_records():
    backupDatabase.delete_database()

def create_table_for_records():
    create = u'''create table backupRecords ( requestid       TEXT PRIMARY KEY,
                                            uuid            TEXT,
                                            pathdisk        TEXT,
                                            status          TEXT,
                                            ctime           INTEGER,
                                            filetype        TEXT,
                                            errorcode       INTEGER,
                                            localsize       INTEGER,
                                            remotesize      INTEGER,
                                            remotepath      INTEGER,
                                            msg             TEXT,
                                            param           TEXT)
                    '''
    connection = backupDatabase.get_connection()
    backupDatabase.execute_sql(connection, create, write=True)
    connection.close()

def insert_backup_record(req):
    msg = req.msg
    param = req.param
    request_id = req.getId()
    ctime = param.get(u'ctime', int(time.time()))
    uuid = param.get(u'uuid')
    path_disk = param.get(u'path_disk')
    path = param.get(u'path')
    status = param.get(u'status', request.STATUS_PENDING)
    errorcode = param.get(u'error_code', 0)
    remotepath = param.get(u'remote_path', None)
    remotesize = param.get(u'remote_size', 0)
    filetype = param.get(u'filetype', None)
    local_size = param.get(u'local_size', None)

    if filetype == None or local_size == None:
        if isfile(path):
            filetype = u'f'
            local_size = getsize(path)
        else:
            filetype = u'd'
            local_size = 0

    parameter = dict(path=path, path_disk=path_disk, uuid=uuid)
    insert = u'''insert into backupRecords (  requestid,
                                            uuid,
                                            pathdisk,
                                            status,
                                            ctime,
                                            filetype,
                                            errorcode,
                                            localsize,
                                            remotesize,
                                            remotepath,
                                            msg,
                                            param)
                values (?,?,?,?,?,?,?,?,?,?,?,?)
        '''
    #logger.debug(insert)
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, insert, \
                                 (request_id, uuid, path_disk, status, ctime, \
                                  filetype, errorcode, local_size, remotesize, remotepath, msg, json.dumps(parameter)), \
                                 write=True)
    if res.get(u'error_code') == errors.DATABASE_TABLE_NOT_EXIST:
        create_table_for_records()
        res = backupDatabase.execute_sql(connection, insert, \
                                 (request_id, uuid, path_disk, status, ctime, \
                                  filetype, errorcode, local_size, remotesize, remotepath, msg, json.dumps(parameter)), \
                                 write=True)
    else:
        res = {u'result':1, u'error_code':errors.DATABASE_ERROR}

    connection.close()
    return res

def get_backup_records(req):
    param = req.param
    start = int(param.get(u'start', u'0'))
    count = int(param.get(u'count', u'-1'))
    records = []

    select = u''' select requestid, ctime, status, remotepath, remotesize, localsize, filetype, errorcode, uuid, pathdisk
                from backupRecords
                order by ctime desc
                limit ?,?
            '''
    logger.debug(select)
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, select, (start, count))

    error_code = res.get(u'error_code', 0)
    if error_code == errors.DATABASE_TABLE_NOT_EXIST:
        create_table_for_records()
        return {u'result':0, u'data':[]}
    elif error_code:
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    for row in res.get(u'data'):
        recd = {}
        size = row[4]
        if size == 0:
            size = row[5]
        recd.update(dict(request_id=row[0], ctime=row[1], status=row[2], remote_path=row[3],size=size,\
                         filetype=row[6],errCode=row[7], uuid=row[8], path_disk=row[9]))
        records.append(recd)

    connection.close()
    return {u'result':0, u'data':records}

def get_backup_record_by_path(req):
    param = req.param
    uuid = param.get(u'uuid')
    path_disk = param.get(u'path_disk')
    record = {}

    select = u'''select requestid, uuid, pathdisk, msg, param, status
                from backupRecords
                where uuid=?
                and pathdisk=?
            '''
    #logger.debug(select)
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, select, (uuid, path_disk))

    error_code = res.get(u'error_code', 0)
    if error_code == errors.DATABASE_TABLE_NOT_EXIST:
        create_table_for_records()
        return {u'result':0, u'data':{}}
    elif error_code:
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    data = res.get(u'data').fetchall()
    if data:
        row = data[0]
        record.update(dict(request_id=row[0], uuid=row[1], path_disk=row[2], msg=row[3], param=json.loads(row[4]), status=row[5]))

    connection.close()
    return {u'result':0, u'data':record}

def get_backup_record_by_req_id(req):
    param = req.param
    request_id = param.get(u'request_id')

    select = u'''select requestid, uuid, pathdisk, status, errorcode
                from backupRecords
                where requestid=?
            '''
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, select, (request_id, ))

    error_code = res.get(u'error_code', 0)
    if error_code == errors.DATABASE_TABLE_NOT_EXIST:
        create_table_for_records()
        return {u'result':1, u'error_code':errors.JOB_NOT_EXISTS}
    elif error_code:
        return {u'result':1, u'error_code':errors.DATABASE_ERROR}

    cursor = res.get(u'data')
    data = cursor.fetchall()
    if not data:
        return {u'result':1, u'error_code':errors.JOB_NOT_EXISTS}
    else:
        row = data[0]
        record = dict(request_id=row[0], uuid=row[1], path_disk=row[2], status=row[3], error_code=row[4])
    connection.close()

    #logger.debug(u'get record %s' % repr(record))
    return {u'result':0, u'data':record}

def paused_all_unfinished_records():
    logger.debug(u'Paused all unfinished records...')
    connection = backupDatabase.get_connection()
    query = u'''update backupRecords
                set status=?, errorcode=?
                where status=?
                or status=?
            '''
    backupDatabase.execute_sql(connection, \
                                 query, \
                                 (request.STATUS_PAUSED, \
                                     errors.UNKNOWN_ERROR, \
                                     request.STATUS_PENDING, \
                                     request.STATUS_PROCESSING),\
                                 write=True)
    connection.commit()
    connection.close()

def update_backup_record(req):
    param = req.param
    status = param.get(u'status', None)
    error_code = param.get(u'error_code', 0)
    ctime = param.get(u'ctime', 0)
    parameter = param.get(u'parameter', None)
    remote_path = param.get(u'remote_path', None)
    remotesize = param.get(u'remotesize', 0)
    request_id = param.get(u'request_id')
    args = []

    update = u'''update backupRecords  set'''
    sub_string = u''

    if status:
        sub_string += u' status=?,'
        args.append(status)

    if error_code:
        sub_string += u' errorcode=?,'
        args.append(error_code)

    if ctime:
        sub_string += u' ctime=?,'
        args.append(ctime)

    if parameter:
        sub_string += u' param=?,'
        args.append(parameter)

    if remote_path:
        sub_string += u' remotepath=?,'
        args.append(remote_path)

    if remotesize:
        sub_string += u'remotesize=?,'
        args.append(remotesize)

    update += sub_string.strip(u',')
    update += u' where requestid=?'
    args.append(request_id)

    logger.debug(update)
    connection = backupDatabase.get_connection()
    res = backupDatabase.execute_sql(connection, update, tuple(args), write=True)
    if not res.get(u'error_code', 0):
        res = {u'result':0, u'data':connection.total_changes}

    connection.close()
    return res

def handle_deprecated_shelve_data():
    names = []
    baidupcs_job_dir = ur'/data/popoCloudData/CloudBackup/baidupcs/jobs'

    if not exists(baidupcs_job_dir) or not isdir(baidupcs_job_dir):
        return

    logger.debug(u'shelve format records found, loaded it to sqlite3 database')
    for f in os.listdir(baidupcs_job_dir):
        f_name, f_suffix = splitext(f)
        if not f_name or f_name in names: continue
        names.append(f_name)

        try:
            file_path = join(baidupcs_job_dir, f_name)
            f_s = shelve.open(file_path)
            msg = f_s['message']
            param = f_s['param']
            ctime = f_s['ctime']
            status = f_s['status']
            if status in [request.STATUS_PENDING, request.STATUS_PROCESSING, request.STATUS_PAUSED]:
                f_s['status'] = request.STATUS_PAUSED
            request_id = f_s['request_id']
            filetype = f_s['filetype']
            local_size = f_s['local_size']
            uuid_s = param['uuid']
            path_disk = param['path_disk']
            path = param['path']
            error_code = f_s.get('errCode', 0)
            remote_path = f_s.get('remote_path', None)
            f_s.close()
            insert_backup_record(request.Request(msg, dict(path=path, uuid=uuid_s, \
                                                           path_disk=path_disk, ctime=ctime, \
                                                           status=status, remote_path=remote_path, \
                                                           filetype=filetype, local_size=local_size, \
                                                            error_code=error_code), request_id))
        except KeyError, e:
            logger.error(str(e))
            f_s.close()
            logger.error(u'Incomplete job file found, delete %s ' % file_path)
            continue
        logger.debug(u'job file %s loaded into job_indexes' % f_name)

    logger.debug(u'delete shelve job files')
    command = u'rm -r %s' % baidupcs_job_dir
    os.system(command)
