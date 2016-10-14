'''
Created on 2016年3月25日

@author: andy.yang
'''
import os
# import datetime
import logging
from logging.handlers import RotatingFileHandler
import random
import time
import easytrader

from atrader.constants import *
from atrader.util import ahelper,atime
from atrader.dummy_quotation_server import DummyQuotationServer

class NotLoginException(Exception):
    def __init__(self, result=None):
        super(NotLoginException, self).__init__()
        self.result = result

class Account(object):

    INSTANCES = {}
    
    #singleton
    def __new__(cls, account_code):
        instance = cls.INSTANCES[account_code] if account_code in cls.INSTANCES else None
        
        if instance is None:
            instance = super(Account,cls).__new__(cls)
            instance.logger = ahelper.get_custom_logger('account.%s' % account_code)
            if not Config.IS_TEST:
                instance.user = easytrader.use('ht', debug=False)
                instance.user.prepare(ahelper.get_config_path('%s.json' % account_code))
                instance.quotation_server = easyquotation.use("lf")
            cls.INSTANCES[account_code] = instance
            instance.logger.info("initialized Account(%s)", account_code)
            
        return instance
        
    
   
    def autologin(self):
        self.logger.info('account auto-login')
        self.user.autologin()
    
    def buy_or_sell(self, bs_type, symbol, price, qty, retry_count=1):
        result = []
        if Config.IS_TEST:
            _code = symbol + '_' + atime.now().strftime("%H%M%S%f")
            DummyQuotationServer().add_order(symbol, _code, qty, price, bs_type)
            return _code
        
        if bs_type==1:
            result = self.__buy(symbol, price, qty)
        elif bs_type == 2:
            result = self.__sell(symbol, price, qty)
        self.logger.info("BUY_OR_SELL - (stock:%s, bs_type:%s, price:%s, qty:%s), return raw data:%s", 
                    symbol, bs_type, price, qty, result)
        #{'cssweb_code': 'error', 'item': None, 'cssweb_type': 'STOCK_BUY', 'cssweb_msg': '请重新登录'}
        if isinstance(result, dict) and result['cssweb_msg'].find('重新登录')>=0:
            if retry_count>0:
                self.logger.warn('require to login again')
                self.autologin()
                return self.buy_or_sell(bs_type, symbol, price, qty, retry_count=retry_count-1)
            else:
                raise Exception('FAIL TO LOGIN......')
            
        return result[0]["entrust_no"] if result else None
    
    def cancel_order(self, order_code, retry_count=1):
        self.logger.info("ACTION - Cancel Entrust: %s", order_code)
        if Config.IS_TEST:
            return None
        
        _data = self.user.cancel_entrust(order_code)
        self.logger.info("ACTION - Cancel Entrust(%s): %s", order_code, _data)
        #{'cssweb_code': 'error', 'item': None, 'cssweb_type': 'STOCK_BUY', 'cssweb_msg': '请重新登录'}
        if isinstance(_data, dict) and _data['cssweb_msg'].find('重新登录')>=0:
            if retry_count>0:
                self.logger.warn('require to login again')
                self.autologin()
                return self.cancel_order(self, order_code, retry_count=retry_count-1)
            else:
                raise Exception('FAIL TO LOGIN......')
        return _data
    
    def get_orders(self, retry_count=1):
        if Config.IS_TEST:
            return DummyQuotationServer().get_orders()
        
        result = self.user.entrust
        self.logger.debug("get entrust list: %s", result)
        if isinstance(result, list):
            return [{'order_code':e['entrust_no'],'actual_qty':e["business_amount"]} for e in result]
        elif isinstance(result, dict):
            self.logger.warn("raw data to get the entrusts: %s", result)
            #{'cssweb_code': 'success', 'cssweb_type': 'GET_CANCEL_LIST', 'item': None}
            if result['cssweb_code']=='success' and result['item'] is None:
                return []
            elif result['cssweb_msg'].find('重新登录')>=0:
                if retry_count>0:
                    self.logger.warn('require to login again')
                    self.autologin()
                    return self.get_orders(self, retry_count=retry_count-1)
                else:
                    raise Exception('FAIL TO LOGIN......')
            else:
                self.logger.error("UNEXPECTED DATA to get the entrusts")
                raise Exception('UNEXPECTED DATA')
        else:
            self.logger.error("UNEXPECTED DATA to get the entrusts: %s", result)
            raise Exception('UNEXPECTED DATA')
    
    
    def get_order(self, order_code): 
        if Config.IS_TEST:
            return DummyQuotationServer().get_order(order_code)
        
        es = [e for e in self.get_orders() if e["order_code"]==order_code] 
        if es==[]:
            return None # None means done
        else:
            es[0]
#             return Entrust(es[0]["entrust_no"], 
#                            es[0]["entrust_status"], #TODO - status mapping, "1" - pending, "2" - done
#                            es[0]["business_price"], 
#                            es[0]["business_amount"],
#                            es[0]["stock_code"], 
#                            es[0]["entrust_price"], 
#                            es[0]["entrust_amount"], 
#                            es[0]["entrust_bs"] # "1" - buy "2" - sell
#                            )
   
   
    def get_real_stocks(self, codes):
        if Config.IS_TEST:
            _dict = dict()
            qs = DummyQuotationServer()
            for s in codes:
                _dict[s] =  {"now":qs.get_price(s), "close":qs.get_last_close(s)}
            return _dict
        else:
            return self.quotation_server.stocks(codes)
            
    
    
    def __buy(self, code, price, qty):
        self.logger.info("ACTION - BUY! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.buy(code,price, qty)
        
    
    def __sell(self, code, price, qty):
        self.logger.info("ACTION - SELL! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.sell(code, price, qty)
    
    
# class Entrust:
#     def __init__(self, no, status, actual_price, actual_qty=0, stock=None, price=None, qty=None, bs_type=None):
#         self.entrust_no = no
#         self.stock = stock
#         self.price = price
#         self.qty = qty
#         self.status = status
#         self.bs_type = bs_type
#         self.actual_price = actual_price
#         self.actual_qty = actual_qty            
        
        
if __name__ == '__main__':
    Config.PROJECT_PATH = os.path.join(os.getcwd(), '..')
    print('Config: IS_TEST=%s, PROJECT_PATH=%s' % (Config.IS_TEST,Config.PROJECT_PATH))
#     acc = Account('053000017966', is_test=False)
    acc = Account('666623491885')
    code = "002024"
    print('************testing**************')
    print('get balance: %s' % acc.user.balance)
    print('get position: %s' % acc.user.position)
    print('get entrust: %s' % acc.user.entrust)
#     result = acc.buy_or_sell(1, code, 10.1, 100)
#     print('buy result %s' % result)
        
#     print(account.user.get_exchangebill("20160405","20160415"))
    
    
    