'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
# import datetime as _datetime
from atrader.util import ahelper,atime
from atrader.model.base_model import BaseModel 
from atrader.model.strategy_detail import StrategyDetail
from constants import TradeStatus, BsType

class TradeOrder(BaseModel):
    '''
    classdocs
    '''
    strategy_detail = ForeignKeyField(StrategyDetail, related_name='orders')
    order_code = CharField()
    price = DoubleField() #actual price
    qty = IntegerField(null=True) #actual qty
    bs_type = CharField() #buy or sell
    fee = DoubleField()
    
    def calc_fee(self):
        if self.bs_type==BsType.BUY:
            self.fee = ahelper.format_money(self.qty*self.price*0.0003)
        else:
            _amount = self.qty*self.price
            self.fee = ahelper.format_money(_amount*0.0003+max(_amount*0.001,5))
    
    class Meta:
        db_table = 'trade_order'      