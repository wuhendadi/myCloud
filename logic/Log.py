# -*- coding:utf-8 -*-
#author:ZJW

import os
import time
import logging
import UtilFunc

_ElastosServerLogger = None
_CurrentLogFile = None

def _initLog(module, logerFileName):
    if module:
        logger = logging.getLogger(module)
    else:
        logger = logging.getLogger()
    hdlr = _getLogHandler(logerFileName)
    logger.addHandler(hdlr)
    return logger

def getLogDataPath():
    if UtilFunc.isLinuxSystem() :
        path = UtilFunc.getBoxLogPath()
    else:
        path = UtilFunc.getPopoCloudAppDataPath()

    path = os.path.join(path, 'log')
    UtilFunc.makeDirs(path)

    return path

def _getLogFolder():
    logerFolder = os.path.join(getLogDataPath(), 'logs')
    try:
        if os.path.exists(logerFolder) and os.path.isfile(logerFolder):
            os.remove(logerFolder)
        if not os.path.exists(logerFolder):
            os.makedirs(logerFolder)
    except:
        pass

    return logerFolder

def _getLogHandler(logerFileName):
    logerFolder = _getLogFolder()
    logerfile = os.path.join(logerFolder, logerFileName)
    hdlr = logging.FileHandler(logerfile)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    UtilFunc.changeMod(logerfile, 644)
    return hdlr

def clean():
    logerFolder =os.path.join(getLogDataPath(), 'logs')
    if os.path.exists(logerFolder):
        files = os.listdir(logerFolder)
        files.sort(lambda x,y:cmp(os.path.getmtime(os.path.join(logerFolder,x)),os.path.getmtime(os.path.join(logerFolder,y))))
        filesLen = len(files)
        for one_file in files:
            if filesLen > 3:
                one_file_path = os.path.join(logerFolder,one_file).replace('\\','/')
                try:
                    os.remove(one_file_path)
                    filesLen-=1
                except:
                    continue
                    filesLen-=1

def getLogger(name = 'ElastosServer'):
    global _ElastosServerLogger
    global _CurrentLogFile
    logerFileName = time.strftime('ES-%Y-%m-%d.log', time.localtime())
    if not _ElastosServerLogger:
        _ElastosServerLogger = _initLog(name, logerFileName)
        _ElastosServerLogger.setLevel(logging.DEBUG)
        
    elif _CurrentLogFile != logerFileName:
        _ElastosServerLogger.removeHandler(_ElastosServerLogger.handlers[0])
        _ElastosServerLogger.addHandler(_getLogHandler(logerFileName))
        
    _CurrentLogFile = logerFileName
    return _ElastosServerLogger

def debug(msg, name = 'ElastosServer'):
    getLogger(name).debug(msg)
    
def info(msg, name = 'ElastosServer'):
    getLogger(name).info(msg)

def warning(msg, name = 'ElastosServer'):
    getLogger(name).warning(msg)
    
def exception(msg, name = 'ElastosServer'):
    getLogger(name).exception(msg)
    
def error(msg, name = 'ElastosServer'):
    getLogger(name).error(msg)
    
    