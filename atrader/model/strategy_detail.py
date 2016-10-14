'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
# import datetime as _datetime
from atrader.model.base_model import BaseModel
from atrader.model.strategy import Strategy
from atrader.util import ahelper,atime
from atrader.constants import *

class StrategyDetail(BaseModel):
    '''
    classdocs
    '''
    strategy = ForeignKeyField(Strategy, related_name='details')
    top_price = DoubleField()
    bottom_price = DoubleField()
    start_price = DoubleField()
    step_delta_price = DoubleField()
    step_count = IntegerField()
    init_qty = IntegerField()
    step_delta_qty = IntegerField()
    high_stop_ratio = DoubleField()
    low_stop_ratio = DoubleField()
    is_active = BooleanField(default=True)
    init_cash = DoubleField(default=0)
    end_cach = DoubleField(default=0)

      
    @property
    def high_stop_price(self):
        if not hasattr(self, '_high_stop_price'):
            self._high_stop_price = ahelper.format_money(self.top_price*(1+self.high_stop_ratio))
        return self._high_stop_price
    
    @property
    def low_stop_price(self):
        if not hasattr(self, '_low_stop_price'):
            self._low_stop_price = ahelper.format_money(self.bottom_price*(1-self.low_stop_ratio))
        return self._low_stop_price
    
    @property
    def completed_steps(self):
        if not hasattr(self, '_completed_steps'):
            self._completed_steps = [p for p in self.steps if p.status==EntrustStatus.COMPLETED]
        return self._completed_steps
    
    @property
    def open_steps(self):
        if not hasattr(self, '_open_steps'):
            self._open_steps = [p for p in self.steps if p.status==EntrustStatus.OPEN]
        return self._open_steps
  
    
    def step_price(self, _no):
        return ahelper.format_money(self.top_price-_no*self.step_delta_price)
    
    def step_no(self, _price):
        if self.high_stop_price<=_price:
            return FixedFlag.HIGH_STOP
        elif self.top_price<=_price:
            return FixedFlag.SELL_ALL
        elif _price<=self.low_stop_price:
            return FixedFlag.LOW_STOP
        elif _price<=self.bottom_price:
            return FixedFlag.BUY_ALL
        else:
            return int((self.top_price - _price)//self.step_delta_price)
    
    def calc_end_cash(self):
        revenue = sum([_calc_money(o) for o in self.orders])
        return ahelper.format_money(self.init_cash + revenue)
    
    def calc_end_qty(self):
        _day = atime.now().day
        return sum([o.qty if o.bs_type==BsType.BUY else -1*o.qty for o in self.orders if o.created_at.day!=_day])
    
    @classmethod
    def select_open(cls, strategy_id):
        return cls.select().join(Strategy).where(cls.is_active==True, Strategy.id==strategy_id)
    
    class Meta:
        db_table = 'strategy_detail'
    
def _calc_money(order):
    if order.bs_type==BsType.BUY:
        return (order.qty*order.price+order.fee)*-1
    else:
        return order.qty*order.price-order.fee
    