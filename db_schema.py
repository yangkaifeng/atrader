'''
Created on 2016年4月30日

@author: andy.yang
'''
from peewee import *
from atrader.model.base_model import *
from atrader.model.strategy_config import * 
from atrader.model.step_position import *


def create_tabels():
    db.connect()
    models = [StrategyConfig, StepPosition]
    db.drop_tables(models, safe=True)
    db.create_tables(models)
    db.close()
    print('db.create_tables(%s)', models)

def setup_testdata():
    ss = [StrategyConfig(account_code='666623491885', stock_code='002024', unit_qty=100, total_num=10, 
                        start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2),
          StrategyConfig(account_code='666623491888', stock_code='000400', unit_qty=100, total_num=10, 
                        start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
#     s = StrategyConfig.batch_insert(s)
    for s in ss:
        s.save()
    print('insert %s', ss)

if __name__ == '__main__':
    create_tabels()
    setup_testdata()
