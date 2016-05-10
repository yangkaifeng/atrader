'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
import datetime as _datetime
from .base_model import BaseModel
from atrader.util import ahelper


class StrategyConfig(BaseModel):
    '''
    classdocs
    '''
    account_code = CharField()
    stock_code = CharField()
    start_price = DoubleField()
    step_ratio = DoubleField()
    total_num = IntegerField()
    unit_qty = IntegerField()
    high_stop_ratio = DoubleField()
    low_stop_ratio = DoubleField()
    status = IntegerField(default=1) # 1-new, 2-open, 3-close
    created_at = DateTimeField(default=_datetime.datetime.now)
    updated_at = DateTimeField(default=_datetime.datetime.now)
    
    @property
    def step_margin(self):
        if not hasattr(self, '_step_margin'):
            self._step_margin = ahelper.format_money(self.start_price*self.step_ratio)
        return self._step_margin
    
    @property
    def high_stop_price(self):
        if not hasattr(self, '_high_stop_price'):
            self._high_stop_price = ahelper.format_money((self.start_price+self.step_margin)*(1+self.high_stop_ratio))
        return self._high_stop_price
    
    @property
    def low_stop_price(self):
        if not hasattr(self, '_low_stop_price'):
            self._low_stop_price = ahelper.format_money(self.start_price*(1-self.step_ratio*(self.total_num-1))*(1-self.low_stop_ratio))
        return self._low_stop_price
    
    @property
    def completed_steps(self):
        if not hasattr(self, '_completed_steps'):
            self._completed_steps = [p for p in self.steps if p.status==2]
        return self._completed_steps
    
    @property
    def open_steps(self):
        if not hasattr(self, '_open_steps'):
            self._open_steps = [p for p in self.steps if p.status==1]
        return self._open_steps
  

    def __repr__(self):
        return "strategy(stock=%s, unit_qty=%s, total_num=%s, start_price=%s, step_ratio=%s,step_margin=%s,\
        \nsteps=%s,\nopen_steps=%s)" % (self.stock_code,self.unit_qty,self.total_num,self.start_price,self.step_ratio,
                                      self.step_margin,self.completed_steps,self.open_steps)
    @classmethod
    def select_opens(cls):
        return cls.select().where(cls.status==2)
    
