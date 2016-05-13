#!/usr/bin/python
# -*- coding: UTF-8 -*-
import platform,os
import time
import subprocess
import sys
import ctypes
import click
from signal import SIGTERM

import main

def get_sysinfo():
    sys = platform.system()
    return os.getpid(),sys
    
# def get_path():
#     p=os.path.split(os.path.realpath(__file__))  # ('D:\\workspace\\python\\src\\mysql', 'dao.py')
#     p=os.path.split(p[0])
#     if not p:
#         os.mkdir(p)
#     return p[0]

def get_pid_path():
    return os.path.join(os.getcwd(), 'tmp', 'atradr.pid')
#     return get_path() +'/tmp/yqs.pid'

def check_pid(pid = 0,osname=''):
    if pid is None or pid == 0:
        return False
    wincmd = 'tasklist /FI "PID eq %s"  /FI "IMAGENAME eq python.exe "' % str(pid)
    lincmd = 'ps ax |grep %s |grep python' % str(pid)
    cmd,size = (wincmd,150) if osname=='Windows' else (lincmd,20)
    returnstr=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
    data = returnstr.stdout.read()
    return len(data) > size
    
def read_pid():
    if os.path.exists(get_pid_path()):
        try:
            with open(get_pid_path(),'r') as f:
                strpid = f.readline().strip()
                return int(strpid)
        except Exception :
            return None
    return None

def rm_pid():
    if os.path.exists(get_pid_path()):
        os.remove(get_pid_path())
        
def kill_win(pid):
    """kill function for Win32"""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(1, 0, pid)
    return (0 != kernel32.TerminateProcess(handle, 0))

def kill_linux(pid):
    os.kill(pid, SIGTERM)
        
def check_run():
    pid,osname = get_sysinfo()
    if not os.path.exists(get_pid_path()):
        with open(get_pid_path(),'w') as f: f.write(str(pid))
        return False
    
    ''' 开始检查 '''
    rs = check_pid(read_pid(),osname)
    if not rs : 
        with open(get_pid_path(),'w') as f: f.write(str(pid))
    return rs
        
class Control :
    def start(self, is_test, interval, project_path):
        if check_run():
            print('process has run')
        else :
            print('starting...')
            main.main(is_test, interval, project_path) #start
            time.sleep(1)
    
    def stop(self):
        _pid = read_pid()
        _,osname = get_sysinfo()
        if _pid is not None and _pid > 0:
            print('kill %s' % _pid)
            if osname=='Windows':
                kill_win(_pid)
            else:
                kill_linux(_pid)
            rm_pid()
        else :
            print('Process has closed')
            
    def check(self):
        filePid = read_pid()
        if not filePid or not check_run() :
            message = "Process has closed\n"
            sys.stderr.write(message)
        else :
            message = "The process has been run, the process id:%d\n"
            sys.stderr.write(message % filePid)
                
    
    
@click.command()
@click.option('--action', help='start|stop|check|help') 
@click.option('--is_test', default=1, help='0:False,1:True')
@click.option('--quotation_interval', default=5, help='default 5s')   
@click.option('--project_path', default=None, help='main project folder')                                
def run(action, is_test, quotation_interval, project_path):
    contr=Control()
    if 'start' == action:
        contr.start(False if is_test==0 else True, quotation_interval, project_path)
    elif 'stop' == action:
        contr.stop()
    elif 'check' == action:
        contr.check()    
        
if __name__ == '__main__':
    run()            