'''
Created on 2016年8月27日

@author: andy.yang
'''
import tushare as ts
import random
import datetime,time
import logging

logger = logging.getLogger(__name__)

class DummyQuotationServer(object):
    INSTANCES = {}
#     TICKET = None
    START = '2016-01-01'
    
    #singleton
    def __new__(cls, ticket=None):
        if ticket is None:
            if len(cls.INSTANCES)>0:
                instance = list(cls.INSTANCES.values())[0]
            else:
                instance = super(DummyQuotationServer,cls).__new__(cls)
        else:
            instance = cls.INSTANCES[ticket] if ticket in cls.INSTANCES else None
        
        if instance is None:
            instance = super(DummyQuotationServer,cls).__new__(cls)
            kline_df = ts.get_hist_data(code=ticket,start=cls.START)
            instance.df=kline_df.loc[:,['open','high','low','close']].sort_index() 
            instance.size=instance.df.index.size
            instance.idx=0
            instance.p_idx=0 # 0,1,2,3
            instance.p_list=[]
            instance.row = instance.df.iloc[instance.idx]
            cls.INSTANCES[ticket] = instance
            
        return instance
    
    # a datetime indicates '2016-08-01 10:' or  '2016-08-01 15:'
    def date(self):
        if hasattr(self,'idx'):
            _dt = datetime.datetime.strptime(self.row.name,'%Y-%m-%d')
            _hour = 15 if self.idx>self.size else 10
            return datetime.datetime.now().replace(year=_dt.year,month=_dt.month,day=_dt.day,hour=_hour)
        else:
            _dt = datetime.datetime.strptime('2016-08-26','%Y-%m-%d')
            return datetime.datetime.now().replace(year=_dt.year,month=_dt.month,day=_dt.day,hour=10)
    
    def price(self):
        if self.p_idx==0:
            time.sleep(0.1)
            if self.idx<self.size:
                self.row = self.df.iloc[self.idx]
            if random.choice(['low','high'])=='low':
                self.p_list = [self.row.open, self.row.low, self.row.high, self.row.close]    
            else:
                self.p_list = [self.row.open, self.row.high, self.row.low, self.row.close]  
            self.idx += 1
                    
        _price = self.p_list[self.p_idx]
        if self.p_idx==3:            
            self.p_idx = 0
        else:
            self.p_idx += 1
        logger.info("DUMMY QUOTATION: date/%s price/%s",self.row.name, _price)
        return _price
                
    
    
    