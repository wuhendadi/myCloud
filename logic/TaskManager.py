# -*- coding: utf-8 -*-

import time
import threadpool
import traceback
import threading
import Log
from collections import deque


local_data = threading.local()

def _handle_task_exception(request, exc_info):
    Log.debug('_handle_task_exception')
    traceback.print_exception(*exc_info)
    
def _task_return(request, result):
    Log.debug('_task_return')

def taskIsCanceled():
    taskControler = local_data._taskControler
    canceled = (taskControler.getOwner() != local_data._reqId)
    return canceled

def _do_task(reqId, taskControler, callable_, args):
    local_data._taskControler = taskControler
    local_data._reqId = reqId
    
    result = None
    try:
        if taskControler.wait(reqId): 
            result = callable_(*args)
    except:
        result = None
        Log.debug(traceback.format_exc())

    taskControler.removeWaiter(reqId)
    local_data._taskControler = None
    local_data._reqId = None
    return result

class TaskContoler:
    def __init__(self):
        self.owner = None
        self.waiters = deque()
        self.mutex = threading.RLock()
        self.event = threading.Event()
    
    def setOwner(self, id):
        self.mutex.acquire()
        self.owner = id
        self.mutex.release()
        self.event.set()
    
    def getOwner(self):
        self.mutex.acquire()
        ret = self.owner
        self.mutex.release()
        return ret
    
    def addWaiter(self, id):
        self.mutex.acquire()
        self.waiters.append(id)
        self.mutex.release()
        self.event.set()
        
    def removeWaiter(self, id):
        self.mutex.acquire()
        if id != self.waiters[0]:
            self.mutex.release()
            raise Exception('TaskContoler', 'removeWaiter error')
        
        self.waiters.popleft()
        self.mutex.release()
        self.event.set()
        
    def wait(self, id):
        while True:
            self.mutex.acquire()
            canceled = (id != self.owner)
            waitOK = (id == self.waiters[0])
            self.mutex.release()
            if canceled:
                #Log.debug('wait canceled 1')
                return False
            
            if waitOK:
                return True
            
            self.event.wait()
            self.event.clear()
            
            self.mutex.acquire()
            canceled = (id != self.owner)
            waitOK = (id == self.waiters[0])
            self.mutex.release()
            
            if canceled:
                #Log.debug('wait canceled 2')
                return False
            
            if waitOK:
                return True
                
class TaskManager:
    def __init__(self, num_workers = 2):
        self.pool = threadpool.ThreadPool(num_workers)
        self.taskControlerMap = {}
        self.mutex = threading.RLock()
    
    def addTask(self, id, callable_, args):
        self.mutex.acquire()
        taskControler = None
        if id in self.taskControlerMap:
            taskControler = self.taskControlerMap[id]
        else:
            taskControler = TaskContoler()
            self.taskControlerMap[id] = taskControler
        
        reqId = time.clock()
        taskControler.addWaiter(reqId)
        taskControler.setOwner(reqId)
        
        reqArgs = [reqId, taskControler, callable_, args]
        req  = threadpool.WorkRequest(_do_task, reqArgs, None, callback=_task_return,
                    exc_callback=_handle_task_exception)
        
        self.pool.putRequest(req)
        self.mutex.release()
        
    def cancelAllTask(self, id):
        if id not in self.taskControlerMap:
            return False
        taskControler = self.taskControlerMap[id]
        taskControler.setOwner(None)
        return True
    
    def waitForAllTaskDone(self):
        self.pool.wait()
        
    def isCanceled(self, id):
        return self.taskControlerMap[id].getOwner() == None
        

class TestClass:
    def __init__(self):
        pass
    
    def testFunc(self, arg1, arg2):
        print 'testFunc:'+arg1+','+arg2
    
     
if __name__ == '__main__':
    manager = TaskManager()
    def test1(arg1, arg2):
        while True:
            print 'test1:'+arg1+','+arg2
            time.sleep(1)
            if taskIsCanceled():
                print 'test1 canceld'
                return
        
    def test2(arg1, arg2):
        while True:
            print 'test2:'+arg1+','+arg2
            time.sleep(1)
            if taskIsCanceled():
                print 'test2 canceld'
                return
        
    manager.addTask(1, test1, ('a', 't1'))
    c = TestClass()
    manager.addTask(2, TestClass.testFunc, (c, 'b', 't2'))
    
    time.sleep(5)
    manager.addTask(1, test1, ('c', 't3'))
    
    time.sleep(5)
    manager.addTask(1, test1, ('d', 't4'))
    manager.addTask(1, test1, ('e', 't5'))
    manager.addTask(1, test1, ('f', 't6'))
    manager.addTask(1, test1, ('g', 't7'))
    manager.addTask(1, test1, ('h', 't8'))
    manager.addTask(1, test1, ('i', 't9'))
    
    while True:
        time.sleep(10)