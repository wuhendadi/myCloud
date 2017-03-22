# -*- coding: utf8 -*-  
# code by Shurrik
  
import threading
import time
import httplib  
HOST = "www.bba789.com";  
PORT = 8888
URI = "/"
TOTAL = 0 
SUCC = 0 
FAIL = 0
EXCEPT = 0 
MAXTIME=0  
MINTIME=100
GT3=0
LT3=0

class RequestThread(threading.Thread):  
    
    def __init__(self, thread_name, flag):  
        threading.Thread.__init__(self)  
        self.test_count = 0
        self.flag = flag
  
    def run(self):
        self.test_performace()
 
    def test_performace(self):  
        global TOTAL  
        global SUCC  
        global FAIL  
        global EXCEPT  
        global GT3  
        global LT3  
        try:  
            st = time.time()  
            conn = httplib.HTTPConnection(HOST, PORT, False)    
            conn.request('GET', URI)  
            res = conn.getresponse()    
            #print 'version:', res.version    
            #print 'reason:', res.reason    
            #print 'status:', res.status    
            #print 'msg:', res.msg    
            #print 'headers:', res.getheaders()  
            if res.status == 200:  
                TOTAL+=1  
                SUCC+=1  
            else:  
                TOTAL+=1  
                FAIL+=1  
            time_span = time.time()-st  
            print '%s:%f\n'%(self.name,time_span)  
            self.maxtime(time_span)  
            self.mintime(time_span)  
            if time_span>3:  
                GT3+=1  
            else:  
                LT3+=1                      
        except Exception,e:  
            print e  
            TOTAL+=1  
            EXCEPT+=1  
        conn.close()
          
    def maxtime(self,ts):  
        global MAXTIME  
        print ts  
        if ts>MAXTIME:  
            MAXTIME=ts
              
    def mintime(self,ts):  
        global MINTIME  
        if ts<MINTIME:  
            MINTIME=ts  
          
if __name__ == '__main__': 
    print '===========task start==========='
    START = False
    start_time = time.time()  
    thread_count = 1000  
          
    i = 0  
    while i <= thread_count:  
        t = RequestThread("thread" + str(i), START)  
        t.start()  
        i += 1  
    t=0  
    
    START = True
    
    while TOTAL<thread_count|t>50:  
        print "total:%d,succ:%d,fail:%d,except:%d\n"%(TOTAL,SUCC,FAIL,EXCEPT)  
        print HOST,URI,TOTAL,t  
        t+=1  
        time.sleep(1)  
    print '===========task end==========='  
    print "total:%d,succ:%d,fail:%d,except:%d"%(TOTAL,SUCC,FAIL,EXCEPT)  
    print 'response maxtime:',MAXTIME  
    print 'response mintime',MINTIME  
    print 'great than 3 seconds:%d,percent:%0.2f'%(GT3,float(GT3)/TOTAL)  
    print 'less than 3 seconds:%d,percent:%0.2f'%(LT3,float(LT3)/TOTAL)  