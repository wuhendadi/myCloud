#!/usr/bin/env python

import time
import os

LOG_FILE='openvpn_setup.log'

def setLogFile(str):
    global LOG_FILE
    if os.path.isfile(str):
        os.remove(str)
    LOG_FILE=str

def getLogFile():
    global LOG_FILE
    return LOG_FILE

def writeFileByMode(fileName, str, mode):
    if mode is None:
        mode='w'
    try:
        f=open(fileName, mode)
        try:
            f.write(str)
            return True
        finally:
            f.close()
    except IOError:
        print ("\r\n" + fileName + " - Can't write the file! Please confirm the write permission")
        return False

def writeFile(fileName, str):
    return writeFileByMode(fileName , str, 'w')

def readfile(filename):
    global loglist
    try:  
        f = open(filename, 'r')
        try:
            return f.read()
        finally:
            f.close()
    except ioerror:
        loglist.append("\r\n" + filename + " - can't open the file! your maybe first run the script, or confirm the read permission!")
        return none

def writeLog(str):
    global LOG_FILE
    timeStr = time.strftime('%Y-%m-%-d %H:%M:%S: ', time.localtime(time.time()))
    writeFileByMode(LOG_FILE, timeStr, 'a')
    writeFileByMode(LOG_FILE, str, 'a')    
    writeFileByMode(LOG_FILE, '\n', 'a')    


#if __name__ == '__main__':
#    logList.append("\r\n-------------------")
#    logList.append("\r\ntest")
#    logList.append("\r\nemma")
#    writeLog("".join(logList));

