#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys,platform,os, atexit, string
import time
import subprocess
import ctypes
import click
from signal import SIGTERM

import main




class Daemon:    
    def __init__(self, pidfile, is_test, quotation_interval, project_path, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):    
        #需要获取调试信息，改为stdin='/dev/stdin', stdout='/dev/stdout', stderr='/dev/stderr'，以root身份运行。    
        self.stdin = stdin    
        self.stdout = stdout    
        self.stderr = stderr    
        self.pidfile = pidfile   
        self.is_test = is_test
        self.quotation_interval = quotation_interval
        self.project_path = project_path 
        
    def _daemonize(self):    
        try:    
            pid = os.fork()        #第一次fork，生成子进程，脱离父进程    
            if pid > 0:    
                sys.exit(0)            #退出主进程    
        except OSError as e:    
            sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))    
            sys.exit(1)    
        
        os.chdir("/")            #修改工作目录    
        os.setsid()                #设置新的会话连接    
        os.umask(0)                #重新设置文件创建权限    
        
        try:    
            pid = os.fork() #第二次fork，禁止进程打开终端    
            if pid > 0:    
                sys.exit(0)    
        except OSError as e:    
            sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))    
            sys.exit(1)    
        
        #重定向文件描述符    
        sys.stdout.flush()    
        sys.stderr.flush()    
        si = open(self.stdin, 'r')    
        so = open(self.stdout, 'a+')    
        se = open(self.stderr, 'a+')    
        os.dup2(si.fileno(), sys.stdin.fileno())    
        os.dup2(so.fileno(), sys.stdout.fileno())    
        os.dup2(se.fileno(), sys.stderr.fileno())    
        
        #注册退出函数，根据文件pid判断是否存在进程    
        atexit.register(self.delpid)    
        pid = str(os.getpid())    
        open(self.pidfile,'w+').write('%s\n' % pid)    
        
    def delpid(self):    
        os.remove(self.pidfile)    
    
    def start(self):    
        #检查pid文件是否存在以探测是否存在进程    
        try:    
            pf = open(self.pidfile,'r')    
            pid = int(pf.read().strip())    
            pf.close()    
        except IOError:    
            pid = None    
        
        if pid:    
            message = 'pidfile %s already exist. Daemon already running!\n'    
            sys.stderr.write(message % self.pidfile)    
            sys.exit(1)    
            
        #启动监控    
        self._daemonize()    
        self._run()    
    
    def stop(self):    
        #从pid文件中获取pid    
        try:    
            pf = open(self.pidfile,'r')    
            pid = int(pf.read().strip())    
            pf.close()    
        except IOError:    
            pid = None    
        
        if not pid:     #重启不报错    
            message = 'pidfile %s does not exist. Daemon not running!\n'    
            sys.stderr.write(message % self.pidfile)    
            return    
    
        #杀进程    
        try:    
            while 1:    
                os.kill(pid, SIGTERM)    
                time.sleep(0.1)    
                #os.system('hadoop-daemon.sh stop datanode')    
                #os.system('hadoop-daemon.sh stop tasktracker')    
                #os.remove(self.pidfile)    
        except OSError as err:    
            err = str(err)    
            if err.find('No such process') > 0:    
                if os.path.exists(self.pidfile):    
                    os.remove(self.pidfile)    
            else:    
                print(str(err))    
                sys.exit(1)    
    
    def restart(self):    
        self.stop()    
        self.start()    
    
    def _run(self):    
        """ run your fun"""    
        main.main(self.is_test, self.quotation_interval, self.project_path) #start
            
class DaemonWin :
    
    def __init__(self, pidfile, is_test, quotation_interval, project_path):
        self.pidfile = pidfile
        self.is_test = is_test
        self.quotation_interval = quotation_interval
        self.project_path = project_path
    
    def start(self):
        if self._check_run():
            print('process has run')
        else :
            print('starting...')
            self._run()
            time.sleep(1)
    
    def stop(self):
        self._kill()
        print('Process has closed')
            
    def restart(self):
        self.stop()
        self.start()
        
    def _run(self):
        main.main(self.is_test, self.quotation_interval, self.project_path) #start
    
#     def get_pid_path(self):
#         return os.path.join(os.getcwd(), 'tmp', 'atrader.pid')
#     return get_path() +'/tmp/yqs.pid'

    def _check_pid(self, pid = 0,osname='Windows'):
        if pid is None or pid == 0:
            return False
        wincmd = 'tasklist /FI "PID eq %s"  /FI "IMAGENAME eq python.exe "' % str(pid)
        lincmd = 'ps ax |grep %s |grep python' % str(pid)
        cmd,size = (wincmd,150) if osname=='Windows' else (lincmd,20)
        returnstr=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
        data = returnstr.stdout.read()
        return len(data) > size
        
    def _read_pid(self):
        if os.path.exists(self.pidfile):
            try:
                with open(self.pidfile,'r') as f:
                    strpid = f.readline().strip()
                    return int(strpid)
            except Exception :
                return None
        return None
    
#     def rm_pid(self):
#         if os.path.exists(self.pidfile):
#             os.remove(self.pidfile)
            
    def _kill(self):
        pid = self._read_pid()
        if pid is not None and pid > 0:
            """kill function for Win32"""
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, 0, pid)
            return (0 != kernel32.TerminateProcess(handle, 0))
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
    
           
    def _check_run(self):
        pid = os.getpid()
        if not os.path.exists(self.pidfile):
            with open(self.pidfile,'w') as f: f.write(str(pid))
            return False
        
        ''' 开始检查 '''
        rs = self._check_pid(self._read_pid())
        if not rs : 
            with open(self.pidfile,'w') as f: f.write(str(pid))
        return rs
    
    
@click.command()
@click.option('--action', help='start|stop|restart|help') 
@click.option('--is_test', default=1, help='0:False,1:True')
@click.option('--quotation_interval', default=5, help='default 5s')   
@click.option('--project_path', default=None, help='main project folder')                                
def run(action, is_test, quotation_interval, project_path):
    os_name = platform.system()
    istest = False if is_test==0 else True
    if os_name == 'Windows':
        pidfile = os.path.join(os.getcwd(), 'tmp', 'atrader.pid')
        daemon = DaemonWin(pidfile, istest, quotation_interval, project_path)
    elif os_name == 'Linux':
        pidfile = '/tmp/atrder_process.pid'
        logfile = os.path.join(os.getcwd(), 'daemon.log')
        if project_path is None:
            project_path = os.getcwd()
        daemon = Daemon(pidfile, istest, quotation_interval, project_path, 
                        stdout=logfile, stderr=logfile)
        
    if 'start' == action:
        daemon.start()
    elif 'stop' == action:
        daemon.stop()
    elif 'restart' == action:
        daemon.restart()    
        
if __name__ == '__main__':
    run()            