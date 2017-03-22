import os
import sys
import time

LOG_FILE_PATH = '/data/popoCloudData/log/thunder.log'
LOG_FILE_PATH_old = '/data/popoCloudData/log/thunder_backup.log'
## define the max file size to 1*1024*1024  bytes
MAX_LOG_FILE_SIZE =  1048576

MODE_ENGINEER = 0
MODE_USER     = 1

LEVEL_DEBUG = 'DEBUG:'
LEVEL_INFO = 'INFO:'
LEVEL_ERR = 'ERROR:'
LEVEL_WAR = 'WARNING:'

mode = MODE_USER

def get_time_string():
    time_string = time.strftime('%m-%d-%H:%M:%S:',time.localtime())
    return time_string

def log(line, level_string):
    global mode

    if(mode == MODE_USER):
        if(level_string == LEVEL_DEBUG):
            return

    time_s = get_time_string()
    string = time_s + level_string + line

    file = open(LOG_FILE_PATH, 'a')

    ## If file size large than 10M bytes, backup it, creat a new file.
    if file.tell() >= MAX_LOG_FILE_SIZE:
        file.close()
        os.rename(LOG_FILE_PATH, LOG_FILE_PATH_old)
        file = open(LOG_FILE_PATH, 'a')

    file.write(string)
    file.close()

def log_info(TAG, string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_INFO)

def log_err(TAG, string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_ERR)

def log_war(TAG, string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_WAR)

def log_debug(TAG, string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_DEBUG)

def set_mode(string):
    global mode

    if(string == 'engineer'):
        mode = MODE_ENGINEER
    else:
        mode = MODE_USER
