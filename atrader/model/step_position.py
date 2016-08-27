'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
# import datetime as _datetime
from atrader.util import ahelper
from atrader.model.base_model import BaseModel 
from atrader.model.strategy_config import StrategyConfig
from email.policy import default
import atrader.util.time as atime

class StepPosition(BaseModel):
    '''
    classdocs
    '''
    strategy = ForeignKeyField(StrategyConfig, related_name='steps')
    source = ForeignKeyField('self', related_name='children', null=True)
    step_no = IntegerField()
    step_price = DoubleField()
    step_qty = IntegerField()
    price = DoubleField() #actual price
    qty = IntegerField(null=True) #actual qty
    bs_type = IntegerField()
    entrust_no = CharField()
    status = IntegerField()
    created_at = DateTimeField(default=atime.now) #TODO: now or now()?
    updated_at = DateTimeField(default=atime.now)
    
#     class Meta:
#         order_by = ('id') 
        
    def __repr__(self):
        if self.source is None:
            return "\nStepPosition{id:%s,source:None,step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,entrust_no:%s,status:%s,strategy_id:%s,created_at:%s}"\
                 % (self.id, self.step_no,self.step_price,self.step_qty,self.price,self.bs_type,self.entrust_no,self.status,self.strategy_id,self.created_at)
        else:
            return "\nStepPosition{id:%s,source:{bs_type=%s,price=%s,step_qty=%s},step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,entrust_no:%s,status:%s,strategy_id:%s,created_at:%s}"\
                 % (self.id, self.source.bs_type,self.source.price,self.source.step_qty,self.step_no,self.step_price,self.step_qty,
                    self.price,self.bs_type,self.entrust_no,self.status,self.strategy_id,self.created_at)
    
