'''
Created on 2016年4月30日

@author: andy.yang
'''
import os
from peewee import *
import click

from atrader.constants import *
from atrader.model.base_model import *
from atrader.model.strategy_config import * 
from atrader.model.step_position import *
from atrader.model.strategy import Strategy
from atrader.model.strategy_detail import StrategyDetail
from atrader.model.trade_order import TradeOrder
from atrader.model.trade_step import TradeStep
from constants import StrategyType, StrategyStatus


def create_tables():
    db.connect()
    models = [Strategy, StrategyDetail, TradeOrder, TradeStep]
#     db.drop_tables(models, safe=True)
    db.create_tables(models)
    db.close()
    print('db.create_tables(%s)' % models)

# def test_data():
#     ss = [StrategyConfig(account_code='666623491885', stock_code='002024', unit_qty=100, total_num=10, 
#                         start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2),
#           StrategyConfig(account_code='666623491888', stock_code='000400', unit_qty=100, total_num=10, 
#                         start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
#     for s in ss:
#         s.save()
#     print('insert %s' % ss)
#     
# def prod_data():
#     ss = [StrategyConfig(account_code='666623491885', stock_code='000400', unit_qty=200, total_num=8, 
#                         start_price=15.87, step_ratio=0.0162, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
#     for s in ss:
#         s.save()
#     print('insert %s' % ss)

def config(code,unit_qty,total_num,start_price,step_ratio,lstop_ratio,hstop_ratio,account='666623491885'):
    s = StrategyConfig.create(account_code=account, stock_code=code, status=StrategyStatus.ACTIVE,
                          unit_qty=unit_qty, total_num=total_num, start_price=start_price, 
                          step_ratio=step_ratio, low_stop_ratio=lstop_ratio, high_stop_ratio=hstop_ratio)
    print('create config: %s' % s)
    
def new_strategy(symbol,account_code,budget,fix_loss,param1,param2,type=StrategyType.KLINE_WEEK,status=StrategyStatus.OPEN):
    Strategy.create(symbol=symbol,
                   account_code=account_code,
                   budget=budget,
                   fix_loss=fix_loss,
                   param1=param1,
                   param2=param2,
                   type=type,
                   status=status)

def history(code, qty, price,account='666623491885'):
    configs = StrategyConfig.select_opens()
    _matchs = [c for c in configs if c.stock_code==code and c.account_code==account]
    if len(_matchs)!=1:
        print('no matching strategy configs for %s' % code)
        return
    
    myconfig = _matchs[0]
    steps = [p for p in myconfig.steps if p.status==EntrustStatus.COMPLETED]
    _qty = qty
    _source = None
    if steps==[]:
        last_step = None
    elif steps[-1].bs_type==BsType.BUY:
        last_step = steps[-1]
        _source = last_step.source
    else:
        print('too complex, do nothing')
        return
    
    while last_step is None or (_qty-last_step.step_qty>=myconfig.unit_qty and last_step.step_no<myconfig.total_num):
        _step = StepPosition()
        _step.strategy = myconfig
        _step.source = _source
        _step.step_no = 1 if last_step is None else last_step.step_no+1
        _step.step_price = myconfig.start_price if last_step is None else ahelper.format_money(last_step.step_price-myconfig.step_margin)
        _step.step_qty = myconfig.unit_qty if last_step is None else last_step.step_qty+myconfig.unit_qty
        _step.price = price
        _step.qty = _step.step_qty
        _step.bs_type = BsType.BUY
        _step.entrust_no = 'history'
        _step.status = EntrustStatus.COMPLETED 
        _step.save()
        if _source is None:
            _source = _step
        last_step = _step
        _qty -= last_step.step_qty
        if _qty-last_step.step_qty<myconfig.unit_qty:
            print('remaining qty=%s' % _qty)

def prod_0712():
    config('000400',500,5,15.71,0.0265,0.01,0.05 )
    config('600009',500,5,29.40,0.0372,0.01,0.05 )
    config('002024',800,5,11.66,0.0360,0.01,0.05 )
    config('000088',800,5,7.03 ,0.0458,0.01,0.05 )
    config('600602',500,5,11.03,0.0585,0.01,0.05 )
    config('002024',500,5,12.30,0.0569,0.01,0.05,account='053000017966')
    config('600372',800,5,26.10,0.0568,0.01,0.05 )
    
    history('000400',800,-13.54)
    history('600009',5400,26.82)
    history('002024',8600,9.95)
    history('000088',1200,26.59)
    history('600602',2800,20.58)
    history('002024',3100,10.93,account='053000017966')
    
# @click.command()
# @click.option('--env', default='dev', help='dev|prod') 
# @click.option('--action', default='all', help='data|table|all')
# def run(env, action):
#     if action in ['table', 'all']:
#         create_tables()
#     if action in ['data', 'all']:
#         if env=='dev':
#             test_data()
#         elif env=='prod':
#             prod_data()


def test_1007():
    new_strategy('000400', 'test_account', 100000, 20000, 2, 5)

if __name__ == '__main__':
    Config.PROJECT_PATH = os.getcwd()
    create_tables()
    test_1007()
