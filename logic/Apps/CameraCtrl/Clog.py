import os
import sys
import time

LOG_FILE_PATH = '/data/popoCloudData/log/cameraCtrl'
MODE_ENGINEER = 0
MODE_USER     = 1

LEVEL_DEBUG = 'DEBUG:'
LEVEL_INFO = 'INFO:'
LEVEL_ERR = 'ERROR:'
LEVEL_WAR = 'WARNING:'
LEVEL_EXCEP = 'EXCEPTION:'
TAG = 'CameraCtrl'

mode = MODE_USER
today = time.strftime('%y-%m-%d',time.localtime())

def get_time_string():
    time_string = time.strftime('%m-%d-%H:%M:%S:',time.localtime())
    return time_string

def log(line, level_string):
    global mode
    global today

    if(mode == MODE_USER):
        if(level_string == LEVEL_DEBUG):
            return

    time_s = get_time_string()
    string = time_s + level_string + line
    
    curday = time.strftime('%Y-%m-%d',time.localtime())
    if curday != today:
        today = curday
    filename = os.path.join(LOG_FILE_PATH, 'CameraCtrl' + today + '.log')
    if not os.path.exists(LOG_FILE_PATH): os.makedirs(LOG_FILE_PATH)
    file = open(filename, 'a')
    file.write(string)
    file.close()

def clean():
    if os.path.exists(LOG_FILE_PATH):
        files = os.listdir(LOG_FILE_PATH)
        files.sort()
        filesLen = len(files)
        for one_file in files:
            if filesLen > 7:
                one_file_path = os.path.join(LOG_FILE_PATH,one_file).replace('\\','/')
                try:
                    os.remove(one_file_path)
                    filesLen-=1
                except:
                    continue
                    filesLen-=1

def info(string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_INFO)

def error(string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_ERR)

def warning(string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_WAR)

def debug(string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_DEBUG)
    
def exception(string):
    line = TAG + ':' + string + '\n'
    log(line, LEVEL_EXCEP)

def set_mode(string):
    global mode

    if(string == 'engineer'):
        mode = MODE_ENGINEER
    else:
        mode = MODE_USER
