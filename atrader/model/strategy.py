'''
Created on 2016年8月18日

@author: andy.yang
'''
from peewee import *
import datetime as _datetime
from atrader.model.base_model import BaseModel
from atrader.constants import *


class Strategy(BaseModel):
    '''
    classdocs
    '''
    
    symbol = CharField()
    account_code = CharField()
    budget = DoubleField()
    fix_loss = DoubleField()
    type = CharField() #StrategyType
    param1 = DoubleField()
    param2 = IntegerField() # max step counts
    status = CharField() #StrategyStatus
    
    @classmethod
    def select_opens(cls):
        return cls.select().where(cls.status==StrategyStatus.OPEN)