'''
Created on 2016年4月4日

@author: andy.yang
'''
import os
import json 
from logging.handlers import RotatingFileHandler
import logging 

from atrader.constants import *

def get_config_path(file_name):
    return os.path.join(PROJECT_PATH, 'config', file_name)

def get_log_path(file_name):
    return os.path.join(PROJECT_PATH, 'log', '%s.log' % file_name)

def get_custom_logger(name):
    _logger = logging.getLogger(name)
    handler = RotatingFileHandler(get_log_path(name), 
                                  maxBytes=10*1024*1024,backupCount=5)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(thread)d - %(name)s - %(levelname)s:   %(message)s')
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    return _logger


def format_money(p):
    return round(p,2)

def format_ratio(r):
    return round(r,4)

def file2dict(path):
    with open(path) as f:
        return json.load(f)
    
    
if __name__ == '__main__':
    print(format_money(10.123123))
    print(format_ratio(0.123123))