import sqlite3
import UtilFunc
from baiducloud import errors
import os
import os.path
import re
from functools import wraps
import utils
import threading

logger = UtilFunc.getLogger()

DB_NAME = u'/data/popoCloudData/CloudBackup/baidupcs/CloudBackup.db'
DB_NAME_BACKUP = u'/data/popoCloudData/CloudBackup/baidupcs/CloudBackup.bak'

DB_OP_LOCK = utils.Lock()

DB_DUMP_COUNT_MAX = 100
DB_DUMP_COUNTER = 0

def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except sqlite3.OperationalError, e:
            logger.error(str(e))
            if str(e) == u'table record already exists':
                res = {u'result':1, u'error_code':errors.DATABASE_TABLE_ALREADY_EXIST}
            elif re.match(u'no such table*', str(e)):
                res = {u'result':1, u'error_code':errors.DATABASE_TABLE_NOT_EXIST}
            else:
                res = {u'result':1, u'error_code':errors.DATABASE_ERROR}
        except sqlite3.DataError:
            logger.error(u'try to restore it')
            restore_database()
            res = {u'result':1, u'error_code':errors.DATABASE_ERROR}
        except Exception, e:
            logger.error(str(e))
            res = {u'result':1, u'error_code':errors.DATABASE_ERROR}
        return res
    return wrapper

def get_connection():
    return sqlite3.connect(DB_NAME)

@handle_exceptions
def execute_sql(connection, query, args=(), write=False, execute_many=False, execute_script=False):
    '''
        write :bool, used to fix multi-thread write conflict
    '''
    global DB_DUMP_COUNTER

    with DB_OP_LOCK:
        if execute_script:
            cursor = connection.executescript(query)
        elif execute_many:
            cursor = connection.executemany(query, args)
        else:
            cursor = connection.execute(query, args)
        connection.commit()

    if write:
        if execute_many or execute_script:
            DB_DUMP_COUNTER += 100
        else:
            DB_DUMP_COUNTER += 1

        if DB_DUMP_COUNTER >= DB_DUMP_COUNT_MAX:
            DB_DUMP_COUNTER = 0
            threading.Thread(target=dump_database).start()

    return {u'result':0, u'data':cursor}

def dump_database():
    logger.debug(u'dump database now')
    connection = get_connection()

    with open(DB_NAME_BACKUP, u'w') as f:
        for line in connection.iterdump():
            f.write("%s\n" % line)

    connection.close()
    logger.debug(u'dump database end')

def restore_database():
    with DB_OP_LOCK:
        os.unlink(DB_NAME)
        connection = get_connection()
        connection.executescript(open(DB_NAME_BACKUP).read())
        connection.commit()
        connection.close()


def delete_database():
    with DB_OP_LOCK:
        if os.path.exists(DB_NAME): os.unlink(DB_NAME)
        if os.path.exists(DB_NAME_BACKUP):os.unlink(DB_NAME_BACKUP)