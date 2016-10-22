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
from sqlalchemy.engine.strategies import strategies

logger = logging.getLogger(__name__)

class DummyQuotationServer(object):
    INSTANCE = None
    START = '2016-01-01'
    END_DATE = None
    LOW_OR_HIGH = 'low_first' # high_first or random
    
    #singleton
    def __new__(cls):
        if cls.INSTANCE is None:
            instance = super(DummyQuotationServer,cls).__new__(cls)
            instance._thread = threading.Thread(target=instance.__run)
            instance.data = {}
            instance.sbs = []
            instance.price_list = {8:{},10:{},12:{},13:{},14:{},15:{}} #{8:{symbol:[price]} }
            instance.date = cls.START #default is start date
            instance.hour = 8 
            cls.INSTANCE = instance
            
        return cls.INSTANCE
    
    def start1(self):
        self._thread.start()
        logger.info('start1: %s is started', __name__)
    
    def __run(self):
        while True:
            hours = [8,10,12,13,14,15]
#             hours.sort()
            for h in hours:
                if self.hour>=10 and self.hour<15:
                    has_order = True
                    has_price = True
                    
                    while has_order and has_price:
                        prices = [lst for lst in self.price_list[self.hour].values() if len(lst)>0]
                        has_price = len(prices)>0
                        orders = [l for l in [len(s.open_steps) for s in self.sbs] if l>0]
                        has_order = len(orders)>0
                        if (not has_price) or (not has_order):
                            break;
                        else:
                            time.sleep(0.5)
                
                self.hour = h
                for symbol in self.data.keys():
                    self.data[symbol]['price'] = self._pop_price(symbol)
                time.sleep(0.5)
            
            is_continue = self.__next_day()
            if not is_continue:
                logger.info('__run: complete testing')
                break;
            
              
    def init(self,symbols, sbs):
        self.sbs = sbs
        for symbol in symbols:
            if symbol in self.data:
                continue
            
            kline_df = ts.get_hist_data(code=symbol,start=self.START,end=self.END_DATE)
            close_list = list(kline_df['close'].values)
            close_list.extend(kline_df.tail(1)['open'])
            close_list.reverse()
            close_list.pop()
            df = kline_df.loc[:,['open','high','low','close']].sort_index()
            df['last_close']=close_list
            row = df.iloc[0]
            self.data[symbol] = {'df':df, 'idx':0,'max_idx':df.index.size-1, 'price':row.last_close, 'last_close':row.last_close}
            logger.info('add_symbols: df-%s', df)
        if symbols:
            self.__next_day()
        else:
            logger.warning('add_symbols: empty symbols')
    
    def __next_day(self):
        if not self.data:
            logger.warning('__next_day: no data')
            return False
        _date = min([d['df'].iloc[d['idx']].name for d in self.data.values()])
        if _date==self.date:
            logger.info('__next_day: at the end of data')
            return False
        
        self.date = _date
        self.hour = 8
#         self.orders.clear()
        for symbol, data in self.data.items():
            row = data['df'].iloc[data['idx']]
            if row.name==_date:
                if self.LOW_OR_HIGH=='low_first' or (self.LOW_OR_HIGH=='random' and random.choice(['low','high'])=='low'):
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
                data['idx'] = data['idx']+1 if data['idx']<data['max_idx'] else data['max_idx']
                data['price'] = row.last_close
                data['last_close'] = row.last_close
            else:
                data['last_close'] = data['price']
                
        logger.info('__next_day: new date is %s:%s', self.date,self.hour)
        logger.info('__next_day: new price_list: %s', self.price_list)
        return True
      
    def now(self):
        _dt = datetime.datetime.strptime(self.date,'%Y-%m-%d')
        return datetime.datetime.now().replace(year=_dt.year,month=_dt.month,day=_dt.day,hour=self.hour)
    
    def get_price(self,symbol):
        return self.data[symbol]['price']
    
    def get_last_close(self, symbol):
        return self.data[symbol]['last_close']
    
#     def add_order(self,symbol,order_code,qty,price,bs_type):
#         if order_code not in self.orders:
#             self.orders[order_code] = {'order_code':order_code, 'symbol':symbol, 'qty':qty, 'actual_qty':0, 'price':price, 'bs_type':bs_type}
    
    def get_order(self,order_code):
        d = [sb for sb in self.sbs if order_code in sb.open_steps]
        if d:
            order = self._build_order(d[0], order_code)
            return order if not self._is_completed_order(order) else None
        else:
            return None
    
    def get_orders(self):
        return [o for o in self._build_orders() if not self._is_completed_order(o)]
        
    
    def _is_completed_order(self, order):
        price = self._pop_price(order['symbol'])
        is_completed = False
        if self.hour<9 or self.hour>=15:
            return False
        elif order['bs_type']==BsType.BUY and order['price']>=price:
#             self.orders.pop(order['order_code'])
            is_completed = True
        elif order['bs_type']==BsType.SELL and order['price']<=price:
#             self.orders.pop(order['order_code'])
            is_completed = True
        logger.debug('_is_completed_order: %s at %s_%s, price=%s, order=%s', is_completed, self.date,self.hour,price, order)
        return is_completed
    
    
    def _build_orders(self):
        orders = []
        for sb in self.sbs:
            orders.extend([self._build_order(sb, code) for code in sb.open_steps])
        return orders
              
    def _build_order(self, sb, order_code):
        step =  sb.open_steps[order_code][0]
        order = {'order_code':order_code, 'symbol':sb.strategy.symbol, 'actual_qty':0, 'price':step.price, 
                 'bs_type':step.bs_type}
        return order
            
              
        
    def _pop_price(self, symbol):
        list_symbol = self.price_list[self.hour][symbol]
        if len(list_symbol)==0:
            _price = self.data[symbol]['price']
        elif len(list_symbol)>1:
            _price = list_symbol.pop()
        else:
            _price = list_symbol[0]
            list_symbol.clear()
        logger.info('_pop_price: pop symbol(%s) price(%s) at %s:%s', symbol, _price, self.date, self.hour)
        return _price