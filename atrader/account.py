'''
Created on 2016年3月25日

@author: andy.yang
'''
import datetime
import logging.config 
import easytrader
# from easytrader import helpers
import random

from constants import *
from atrader.util import ahelper


# logging.config.fileConfig("logging.conf")
# create logger     
logger = logging.getLogger(__name__)


class Account(object):
    '''
    classdocs
    '''
    
    INSTANCES = {}
    
    #singleton
    def __new__(cls, account_code):
        
#         account_code = kw['account_code'] if 'account_code' in kw else ''
        instance = cls.INSTANCES[account_code] if account_code in cls.INSTANCES else None
        if instance is None:
            instance = super(Account,cls).__new__(cls)
            if IS_TEST:
                logger.warning("%s TESTING MODE %s", "#"*6, "#"*6)
            else:
#                 helpers.disable_log() #disable easytrader debug logs
                instance.user = easytrader.use('ht', debug=False)
                instance.user.prepare('config\\%s.json' % account_code)
            cls.INSTANCES[account_code] = instance
            logger.debug("initialized Account(%s)", account_code)
            
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
    def buy_or_sell(self, bs_type, code, price, qty):
        result = []
        if IS_TEST:
            result = [{"entrust_no":datetime.datetime.now().strftime("%Y%m%d%H%M%S")}]
        elif bs_type==1:
            result = self.__buy(code, price, qty)
        elif bs_type == 2:
            result = self.__sell(code, price, qty)
        logger.info("BUY_OR_SELL - (stock:%s, bs_type:%s, price:%s, qty:%s), return raw data:%s", 
                    code, bs_type, price, qty, result)
        return result[0]["entrust_no"] if result else None
    
    def cancel_entrust(self, entrust_no):
        logger.info("ACTION - Cancel Entrust: %s", entrust_no)
        if IS_TEST:
            pass
        else:
            return self.user.cancel_entrust(entrust_no)
        
    def get_entrust(self, entrust_no): 
        if IS_TEST:
            _r = random.uniform(1,100)
            return None if _r>=50 else Entrust(entrust_no, 2, 0)
        else:
            result = self.user.entrust
            if isinstance(result, list):
                es = [e for e in self.user.entrust if e["entrust_no"]==entrust_no] 
                if len(es)>1:
                    #TODO -handle this
                    pass
                elif es==[]:
                    return None # None means done
                else:
                    return Entrust(es[0]["entrust_no"], 
                                   es[0]["entrust_status"], #TODO - status mapping, "1" - pending, "2" - done
                                   es[0]["business_price"], 
                                   es[0]["business_amount"],
                                   es[0]["stock_code"], 
                                   es[0]["entrust_price"], 
                                   es[0]["entrust_amount"], 
                                   es[0]["entrust_bs"] # "1" - buy "2" - sell
                                   )
            else:
                logger.error("Can't find the entrust(%s), raw data: %s", entrust_no, result)
                return None # None means none or cancelled
        
    def __buy(self, code, price, qty):
        logger.info("ACTION - BUY! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.buy(code,price, qty)
        
    
    def __sell(self, code, price, qty):
        logger.info("ACTION - SELL! stock=%s, price=%s, qty=%s", code, price, qty)
        return self.user.sell(code, price, qty)
    
    
class Entrust:
    def __init__(self, no, status, actual_price, actual_qty=None, stock=None, price=None, qty=None, bs_type=None):
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
#     print(id(Account()))
    account = Account('666623491885')
    acc = Account('666623491885')
    code = "002024"
#     print(account.__dict__)
#     print(account.get_stock("600602"))
#     print(account.buy_or_sell(1,code, 11.0, 100))
#     print(account.buy_or_sell(2,code, 12.5, 100))
#     print(account.cancel_entrust("11833"))
    print(account.user.entrust)
    print(acc.get_stock(code))
#     print(account.get_entrust("11834"))
#     print(account.user.get_exchangebill("20160405","20160415"))
    
    
    