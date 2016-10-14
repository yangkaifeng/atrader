'''
Created on 2016年8月27日

@author: andy.yang
'''
import tushare as ts
import random
import datetime,time
import logging
import threading

from atrader.constants import BsType

logger = logging.getLogger(__name__)

class DummyQuotationServer(object):
    INSTANCE = None
    START = '2016-01-01'
    
    #singleton
    def __new__(cls):
        if cls.INSTANCE is None:
            instance = super(DummyQuotationServer,cls).__new__(cls)
            instance.start = cls.START
            instance.data = {}
            instance.orders = {}
            instance.price_list = {8:{},10:{},12:{},13:{},14:{},15:{}} #{8:{symbol:[price]} }
            instance.date = instance.start #default is start date
            instance.hour = 8 
            cls.INSTANCE = instance
            
        return cls.INSTANCE
    
    def start1(self):
        self._thread = threading.Thread(target=self.__run)
        self._thread.start()
        logger.info('%s is started', __name__)
    
    def __run(self):
        while True:
            prices = [lst for lst in self.price_list[self.hour].values() if len(lst)>0]
            if prices==[]:
                hours = [h for h in [8,10,12,13,14,15] if h>self.hour]
                if hours:
                    self.hour = hours[0]
                    logger.debug('new hour=%s', self.hour)
                else:
                    self.__next_day()
                
            time.sleep(0.1)
              
    def add_symbols(self,symbols):
        for symbol in symbols:
            if symbol in self.data:
                continue
            
            kline_df = ts.get_hist_data(code=symbol,start=self.start)
            close_list = list(kline_df['close'].values)
            close_list.extend(kline_df.tail(1)['open'])
            close_list.reverse()
            close_list.pop()
            df = kline_df.loc[:,['open','high','low','close']].sort_index()
            df['last_close']=close_list
            row = df.iloc[0]
            self.data[symbol] = {'df':df, 'idx':0,'max_idx':df.index.size-1, 'price':row.last_close, 'last_close':row.last_close}
        
        self.__next_day()
    
    def __next_day(self):
        _date = min([d['df'].iloc[d['idx']].name for d in self.data.values()])
        self.date = _date
        self.hour = 8
        self.orders.clear()
        for symbol, data in self.data.items():
            if data['idx']>data['max_idx']:
                continue
            
            row = data['df'].iloc[data['idx']]
            if row.name==_date:
                if random.choice(['low','high'])=='low':
                    p1 = row.low
                    p2 = row.high
                else:
                    p1 = row.high
                    p2 = row.low
                self.price_list[8][symbol] = [row.last_close]
                self.price_list[10][symbol] = [p1, row.open]
                self.price_list[12][symbol] = [p1]
                self.price_list[13][symbol] = [p2]
                self.price_list[14][symbol] = [row.close]
                self.price_list[15][symbol] = [row.close]
                data['idx'] = data['idx']+1
                data['price'] = row.last_close
                data['last_close'] = row.last_close
            else:
                data['last_close'] = data['price']
                
        logger.info('new date is %s:%s', self.date,self.hour)
        logger.info('new price_list: %s', self.price_list)
      
    def now(self):
        _dt = datetime.datetime.strptime(self.date,'%Y-%m-%d')
        return datetime.datetime.now().replace(year=_dt.year,month=_dt.month,day=_dt.day,hour=self.hour)
    
    def get_price(self,symbol):
        return self.data[symbol]['price']
    
    def get_last_close(self, symbol):
        return self.data[symbol]['last_close']
    
    def add_order(self,symbol,order_code,qty,price,bs_type):
        if order_code not in self.orders:
            self.orders[order_code] = {'order_code':order_code, 'symbol':symbol, 'qty':qty, 'actual_qty':0, 'price':price, 'bs_type':bs_type}
    
    def get_order(self,order_code):
        if order_code in self.orders:
            return self.orders[order_code]
        else:
            return None
    
    def get_orders(self):
        _orders = []
        del_codes = []
        for _code, _ord in self.orders.copy().items():
            _price = self.pop_price(_ord['symbol'])
            if self.hour<9 or self.hour>=15:
                _orders.append(_ord)
            elif _ord['bs_type']==BsType.BUY and _ord['price']>=_price:
                self.orders.pop(_code)
            elif _ord['bs_type']==BsType.SELL and _ord['price']<=_price:
                self.orders.pop(_code)
            else:
                _orders.append(_ord)
        return _orders
    
    def pop_price(self, symbol):
        list_symbol = self.price_list[self.hour][symbol]
        if len(list_symbol)==0:
            _price = self.data[symbol]['price']
        elif len(list_symbol)>1:
            _price = list_symbol.pop()
        else:
            _price = list_symbol[0]
            list_symbol.clear()
        logger.info('pop symbol(%s) price(%s) at %s:%s', symbol, _price, self.date, self.hour)
        return _price