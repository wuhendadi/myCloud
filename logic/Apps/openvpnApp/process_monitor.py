#!/usr/bin/env python
import threading
import subprocess
import re
#import signal
import os
import platform
import time
import sys
from debug_to_file import DebugToFileClass
from openvpn_error import *

class ProcessMonitor:
    def __init__(self, settings):
        self.settings=settings
        self.alive=True
        self.app_pid=0

        self.pidfile=self.settings.get('PIDFILE')
        #if os.path.exists(self.pidfile):
        #    os.remove(self.pidfile)

        self.logfile=self.settings.get('LOG')
        #if os.path.exists(self.logfile):
        #    os.remove(self.logfile)

        # Get the pid of the current process 
        self.pid=os.getpid()

        #Register the signal handlers so we can exit gracefully when a signal is received
        #signal.signal(signal.SIGTERM, self.signal_handler)      # Terminate Signal (on app process stop, system shutdown etc)
        #signal.signal(signal.SIGINT, self.signal_handler)       # Interrupt Signal (ctrl-c etc)

        self.OVERWRITE_LOG=False
        self.monitor_thread=None
        self.app_process=None
        
    def set_mode(self, mode):
        self.mode = mode
        sys.stdout.write('Mode set to: %s\n' % mode)

    def get_mode(self):        
        return self.mode

    def before_start(self):
        pass
     

    def start(self):

        #sys.stdout.flush()
        #sys.stderr.flush()
        self.so = DebugToFileClass(tag='STDOUT',  filename=self.settings['LOG'], appname=self.settings['APP'], overwrite=self.OVERWRITE_LOG)
        self.se = DebugToFileClass(tag='STDERR', filename=self.settings['LOG'], appname=self.settings['APP'], overwrite=False)
        sys.stdout = self.so
        sys.stderr = self.se

        self.set_mode('starting')
        self.before_start()
        if os.path.exists(self.pidfile) and self.check_process() == 0:
            os.remove(self.pidfile)

        sys.stdout.write("Checking whether the Linux Daemon is already running()...\n")
        # Check for a pidfile (Process ID file) to see if the process is already running
        if os.path.exists(self.pidfile):
            try:
                pf = file(self.pidfile,'r')
                self.app_pid = int(pf.read().strip())
                pf.close()
                # exit if the pid file already exists. Presumably there is already an instance running.
                sys.stderr.write("pidfile %s already exists. The Daemon already running with process ID: %r\n" % (self.pidfile,  self.app_pid))
                return generalErrors[7]
                #sys.exit(1)
            except IOError:
                # error opening the pid file
                sys.stderr.write("Error opening pidfile: %s. You may need to delete it mannually and possibly manually kill the process\n" % self.pidfile)
                return generalErrors[8]
                #sys.exit(1)
                self.app_pid = None
        else:
            self.start_app_process()

        self.alive=True
        self.monitor_thread=None
        self.monitor_thread=threading.Thread(target=self.run) 
        self.monitor_thread.start()
        return True

    def start_app_process(self):
        print 'CMD=',self.settings['CMD']
        self.app_process=subprocess.Popen(self.settings['CMD'], preexec_fn=os.setpgrp)

        self.app_pid=self.app_process.pid
        sys.stdout.write("**** The PROCESS ID for the RUNNING APP is: %s  ****\n" % str(self.app_pid))
        file(self.pidfile,'w+').write("%s\n" % str(self.app_pid))
        self.set_mode('running')
        return self.app_process

    def before_stop(self):
        pass
    
    def stop(self):
        self.set_mode('stopping')
        self.before_stop()  # Pre-stop processing

        self.alive=False #Stop process monitor thread
        if self.monitor_thread is not None:
            self.monitor_thread.join(5)
        self.monitor_thread=None
        self.ret=self.stop_app_process()
        self.on_exit()
        self.cleanup()
        return self.ret

    def stop_app_process(self):

        pid = self.status()

        if not pid:
            sys.stderr.write(" * Daemon is not running so cannot stop it.\n")
            return generalErrors[8]

        sys.stdout.write("(PID: %s) process.stop()...\n" % self.app_pid)
        sys.stdout.write("...Sending SIGTERM to process %s\n" % pid)
        try:
            os.kill(pid, 15)        
            os.kill(-pid,15) #kill all group process
            time.sleep(0.1)
            if self.app_process is not None:
                subprocess.Popen.wait(self.app_process)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                # The process identified by the pid file does not exit
                # So just remove the pid file
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                sys.stderr.write(str(err))
                return generalErrors[8]
                #sys.exit(1)
        return True

    def before_restart(self):
        pass

    def restart(self):
        if not os.path.exists(self.pidfile): #if the process not start, you need start it first
            sys.stdout.write("Pleast call start first...\n")
            return generalErrors[8]

        self.set_mode('restarting')
        self.before_restart()
        
        sys.stdout.write("(PID: %s) Restarting the Linux Daemon...\n")
        self.stop_app_process()          
        self.start_app_process()         

    def check_process(self):
        os.system("ps|grep openvpn>%s"% self.settings['TMP']) 
        if os.path.isfile(self.settings['TMP']): 
            return os.path.getsize(self.settings['TMP']);
        else:
            return 0
        
    def status(self):
        message = ""
        if os.path.exists(self.pidfile) and self.check_process() == 0:
            os.remove(self.pidfile)

        if os.path.exists(self.pidfile):
            try:
                pf = file(self.pidfile,'r')
                pid = int(pf.read().strip())
                pf.close()
                message = " * %s is running (Process ID = %s)\n" % (self.settings['APP'], pid)
            except IOError:
                message = " * %s is running (but can't read the pid file)\n" % (self.settings['APP'],)
                pid = None
        else:
            message = " * %s IS NOT running (no PID file)\n" % (self.settings['APP'],)
            pid = None

        sys.stdout.write(message)
        return pid
             
    def run(self):
        sys.stdout.write('Starting Processing (pid:%s)...\n'  % self.pid)

        while self.alive:
            # Do something. In this case just write a line of text and wait for 1 second, then do it all over again
            #sys.stdout.write('App process is running with a process id (pid) = %s\n' % (self.app_pid))
            if(self.alive == False):
                break

            try:
                time.sleep(3)
            except:
                # traps and ignores any error if an interrupt is received while sleeping/waiting
                pass

            if(self.get_mode()=='restarting'):
                continue

            returncode=subprocess.Popen.poll(self.app_process)
            if returncode is not None:
                sys.stdout.write('App process %s is exit, retrun code=%s\n' % (self.app_pid, returncode))
                subprocess.Popen.wait(self.app_process)
                self.start_app_process()

        sys.stdout.write('...Procesing has ended.\n')

    def on_exit(self):
        pass

    def cleanup(self):
        sys.stdout.write('Cleaning up...')
        
        # Delete the PID file
        if os.path.exists(self.pidfile):
            sys.stdout.write('Deleting the PID file\n')
            os.remove(self.pidfile)
        else:
            sys.stdout.write('PID file does not exist so no need to deleted it\n')

        # Reset stdout and stderr to the terminal
        sys.stdout.write("Resetting STDOUT and STDERR to the terminal...\n")
        sys.stdout.write("..All Done\n")
        sys.stdout = sys.__stdout__         # reset std out
        sys.stderr = sys.__stderr__         # reset std err
        
        #sys.exit(0)

    def signal_handler(self, signum, frame):

        signals = {15:'SIGTERM (TERMinate SIGnal)',  2: 'SIGINT (INTerupt (Ctrl-C) SIGnal)'}

        sys.stdout.write("(pid:%s) DaemonClass.signal_handler(): %s received\n" % (self.pid, signals[signum]))

        self.alive = False

        # Quit gracefully
        self.on_interrupt()

    def on_interrupt(self):
        pass


