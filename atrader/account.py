'''
Created on 2016年3月25日

@author: andy.yang
'''
import os
import datetime
import logging
from logging.handlers import RotatingFileHandler
import random
import time
import easytrader

from atrader.constants import *
from atrader.util import ahelper

class NotLoginException(Exception):
    def __init__(self, result=None):
        super(NotLoginException, self).__init__()
        self.result = result

class Account(object):

    INSTANCES = {}
    
    #singleton
    def __new__(cls, account_code, is_test=True):
        instance = cls.INSTANCES[account_code] if account_code in cls.INSTANCES else None
        
        if instance is None:
            instance = super(Account,cls).__new__(cls)
            instance.logger = ahelper.get_custom_logger('account.%s' % account_code)
            instance.is_test = is_test
            if not instance.is_test:
                instance.user = easytrader.use('ht', debug=False)
                instance.user.prepare(ahelper.get_config_path('%s.json' % account_code))
            cls.INSTANCES[account_code] = instance
            instance.logger.info("initialized Account(%s)", account_code)
            
        return instance
        
    
#     def get_stock(self,code):
#         if IS_TEST:
#             p = ahelper.format_money(self.last_p*random.uniform(0.99,1.01))
#             self.last_p = p
# #             logger2.debug("current price: %s", p)
#             return {"now":p,"ask1":p+0.01, "bid1":p-0.01}
#         else:
#             d = self.quotation.stocks(code)[code]
#             return {"now":d["now"],"ask1":d["ask1"], "bid1":d["bid1"]}    
#     
    
    def autologin(self):
        self.logger.info('account auto-login')
        self.user.autologin()
    
    def buy_or_sell(self, bs_type, code, price, qty):
        result = []
        if self.is_test:
            result = [{"entrust_no":datetime.datetime.now().strftime("%Y%m%d%H%M%S")}]
#             if bs_type==1:
#                 result = [{"entrust_no":datetime.datetime.now().strftime("%Y%m%d%H%M%S")}]
#             else:
#                 result = {'cssweb_code': 'error', 'item': None, 'cssweb_type': 'STOCK_BUY', 'cssweb_msg': '请重新登录'}
        elif bs_type==1:
            result = self.__buy(code, price, qty)
        elif bs_type == 2:
            result = self.__sell(code, price, qty)
        self.logger.info("BUY_OR_SELL - (stock:%s, bs_type:%s, price:%s, qty:%s), return raw data:%s", 
                    code, bs_type, price, qty, result)
        #{'cssweb_code': 'error', 'item': None, 'cssweb_type': 'STOCK_BUY', 'cssweb_msg': '请重新登录'}
        if isinstance(result, dict) and result['cssweb_msg']=='请重新登录':
            self.logger.warn('require to login again')
            raise NotLoginException('re-login')
            
        return result[0]["entrust_no"] if result else None
    
    def cancel_entrust(self, entrust_no):
        self.logger.info("ACTION - Cancel Entrust: %s", entrust_no)
        if self.is_test:
            pass
        else:
            _data = self.user.cancel_entrust(entrust_no)
            self.logger.info("ACTION - Cancel Entrust(%s): %s", entrust_no, _data)
            #{'cssweb_code': 'error', 'item': None, 'cssweb_type': 'STOCK_BUY', 'cssweb_msg': '请重新登录'}
            if isinstance(_data, dict) and _data['cssweb_msg']=='请重新登录':
                self.logger.warn('require to login again')
                raise NotLoginException('re-login')
            return _data
        
    def get_entrust(self, entrust_no): 
        _data = None
        if self.is_test:
            _r = random.uniform(1,100)
            _data = None if _r>=50 else Entrust(entrust_no, 2, 0)
        else:
            result = self.user.entrust
            self.logger.debug("get entrust list: %s", result)
            if isinstance(result, list):
                es = [e for e in self.user.entrust if e["entrust_no"]==entrust_no] 
                if es==[]:
                    _data = None # None means done
                else:
                    _data = Entrust(es[0]["entrust_no"], 
                                   es[0]["entrust_status"], #TODO - status mapping, "1" - pending, "2" - done
                                   es[0]["business_price"], 
                                   es[0]["business_amount"],
                                   es[0]["stock_code"], 
                                   es[0]["entrust_price"], 
                                   es[0]["entrust_amount"], 
                                   es[0]["entrust_bs"] # "1" - buy "2" - sell
                                   )
            elif isinstance(result, dict):
                self.logger.warn("raw data to get the entrust(%s): %s", entrust_no, result)
                #{'cssweb_code': 'success', 'cssweb_type': 'GET_CANCEL_LIST', 'item': None}
                if result['cssweb_code']=='success' and result['item'] is None:
                    _data = None
                elif result['cssweb_msg']=='请重新登录':
                    self.logger.warn('require to login again')
                    raise NotLoginException('re-login')
                else:
                    self.logger.error("UNEXPECTED DATA to get the entrust(%s)", entrust_no)
                    raise Exception('UNEXPECTED DATA')
            else:
                self.logger.error("UNEXPECTED DATA to get the entrust(%s): %s", entrust_no, result)
                raise Exception('UNEXPECTED DATA')
        return _data
   
    def __buy(self, code, price, qty):
        self.logger.info("ACTION - BUY! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.buy(code,price, qty)
        
    
    def __sell(self, code, price, qty):
        self.logger.info("ACTION - SELL! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.sell(code, price, qty)
    
    
class Entrust:
    def __init__(self, no, status, actual_price, actual_qty=0, stock=None, price=None, qty=None, bs_type=None):
        self.entrust_no = no
        self.stock = stock
        self.price = price
        self.qty = qty
        self.status = status
        self.bs_type = bs_type
        self.actual_price = actual_price
        self.actual_qty = actual_qty            
        
    def __repr__(self):
        return "Entrust(entrust_no=%s, stock=%s, price=%s,qty=%s, status=%s,bs_type=%s, actual_price=%s,actual_qty=%s"\
             % (self.entrust_no, self.stock, self.price, self.qty, self.status, self.bs_type,
                self.actual_price,self.actual_qty)   
        
if __name__ == '__main__':
    Config.PROJECT_PATH = os.path.join(os.getcwd(), '..')
    print('PROJECT_PATH=%s' % Config.PROJECT_PATH)
    acc = Account('666623491885', is_test=False)
    code = "002024"
    print('************testing**************')
    for i in list(range(1,10)):
        time.sleep(60*i)
        print('No.%s - balance: %s' % (i,acc.user.balance))
        
#     print(account.user.get_exchangebill("20160405","20160415"))
    
    
    