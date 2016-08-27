'''
Created on 2016年5月2日

@author: andy.yang
'''
import os
import sys
from atrader.dummy_quotation_server import DummyQuotationServer

quoation_path = os.path.join(os.getcwd(), '..', 'easyquotation')
if quoation_path not in sys.path:
    sys.path.append(quoation_path)
trader_path = os.path.join(os.getcwd(), '..', 'easytrader')
if trader_path not in sys.path:
    sys.path.append(trader_path)

from atrader.constants import *
from atrader.main_engine import MainEngine


def main(is_test, quotation_interval, project_path=None):
    Config.IS_TEST = is_test
    if project_path is not None:
        Config.PROJECT_PATH = project_path
    else:
        Config.PROJECT_PATH = os.getcwd()
    print('PROJECT_PATH=%s' % Config.PROJECT_PATH)
    MainEngine(quotation_interval).start()

if __name__ == '__main__':  
    DummyQuotationServer.START='2016-05-01'  
    main(True, 1)