'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
# import datetime as _datetime
from atrader.util import ahelper,atime
from atrader.model.base_model import BaseModel 
from atrader.model.strategy_detail import StrategyDetail
from atrader.constants import TradeStatus

class TradeStep(BaseModel):
    '''
    classdocs
    '''
    strategy_detail = ForeignKeyField(StrategyDetail, related_name='steps')
    source = ForeignKeyField('self', related_name='children', null=True)
    step_no = IntegerField()
    step_price = DoubleField()
    step_qty = IntegerField()
    price = DoubleField() #actual price
    qty = IntegerField(null=True) #actual qty
    bs_type = CharField() #buy or sell
    order_code = CharField()
    status = CharField() # open,completed
    
    @classmethod
    def select_last(cls, detail_id):
        data = cls.select().join(StrategyDetail).where(cls.status==TradeStatus.COMPLETED, StrategyDetail.id==detail_id).order_by(cls.id.desc()).limit(1)
        if data:
            return data[0]
        else:
            return None
    
    @classmethod
    def select_open(cls, detail_id):
        return cls.select().join(StrategyDetail).where(cls.status==TradeStatus.OPEN, StrategyDetail.id==detail_id).order_by(cls.id.asc())
    
    @classmethod
    def update_status(cls, order_code, status):
        query = cls.update(status=status, updated_at=atime.now()).where(cls.order_code==order_code)
        return query.execute()
    
#     @classmethod
#     def bulk_insert(cls, rows):
#         return cls.insert_many(rows).execute()

    def __repr__(self):
        if self.source is None:
            return "\nTradeStep{id:%s,source:None,step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,order_code:%s,status:%s,strategy_detail_id:%s,created_at:%s}"\
                 % (self.id, self.step_no,self.step_price,self.step_qty,self.price,self.bs_type,self.order_code,self.status,self.strategy_detail_id,self.created_at)
        else:
            return "\nTradeStep{id:%s,source:{bs_type=%s,price=%s,step_qty=%s},step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,order_code:%s,status:%s,strategy_detail_id:%s,created_at:%s}"\
                 % (self.id, self.source.bs_type,self.source.price,self.source.step_qty,self.step_no,self.step_price,self.step_qty,
                    self.price,self.bs_type,self.order_code,self.status,self.strategy_detail_id,self.created_at)
    
    
    class Meta:
        db_table = 'trade_step'
        only_save_dirty = True      