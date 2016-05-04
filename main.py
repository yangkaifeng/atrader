'''
Created on 2016年5月2日

@author: andy.yang
'''
import os
import sys

quoation_path = os.path.join(os.getcwd(), '..', 'easyquotation')
if quoation_path not in sys.path:
    sys.path.append(quoation_path)
trader_path = os.path.join(os.getcwd(), '..', 'easytrader')
if trader_path not in sys.path:
    sys.path.append(trader_path)

from atrader.util.ahelper import *
from atrader.main_engine import MainEngine


def main(is_test, quotation_interval, project_path=None):
    global PRJECT_PATH
    if project_path is not None:
        PROJECT_PATH = project_path
    MainEngine(is_test, quotation_interval).start()

if __name__ == '__main__':
    main(True, 1)