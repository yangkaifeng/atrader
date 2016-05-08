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


def create_tabels():
    db.connect()
    models = [StrategyConfig, StepPosition]
    db.drop_tables(models, safe=True)
    db.create_tables(models)
    db.close()
    print('db.create_tables(%s)' % models)

def test_data():
    ss = [StrategyConfig(account_code='666623491885', stock_code='002024', unit_qty=100, total_num=10, 
                        start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2),
          StrategyConfig(account_code='666623491888', stock_code='000400', unit_qty=100, total_num=10, 
                        start_price=10.0, step_ratio=0.01, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
    for s in ss:
        s.save()
    print('insert %s' % ss)
    
def prod_data():
    ss = [StrategyConfig(account_code='666623491885', stock_code='000400', unit_qty=200, total_num=8, 
                        start_price=15.87, step_ratio=0.0162, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
    for s in ss:
        s.save()
    print('insert %s' % ss)

def config(code,unit_qty,total_num,start_price,step_ratio,lstop_ratio,hstop_ratio):
    s = StrategyConfig.create(account_code='666623491885', stock_code=code, status=StrategyStatus.ACTIVE,
                          unit_qty=unit_qty, total_num=total_num, start_price=start_price, 
                          step_ratio=step_ratio, low_stop_ratio=lstop_ratio, high_stop_ratio=hstop_ratio)
    print('create config: %s' % s)
    
def history(code, qty, price):
    configs = StrategyConfig.select_opens()
    _matchs = [c for c in configs if c.stock_code==code]
    if len(_matchs)!=1:
        print('no matching strategy configs for %s' % code)
        return
    
    myconfig = _matchs[0]
    steps = [p for p in myconfig.steps if p.status==EntrustStatus.COMPLETED]
    _qty = qty
    if steps==[]:
        last_step = None
    elif steps[-1].bs_type==BsType.BUY:
        last_step = steps[-1]
    else:
        print('too complex, do nothing')
        return
    
    while last_step is None or (_qty-last_step.step_qty>=myconfig.unit_qty and last_step.step_no<myconfig.total_num):
        _step = StepPosition()
        _step.strategy = myconfig
        _step.source = last_step.source if last_step else None
        _step.step_no = 1 if last_step is None else last_step.step_no+1
        _step.step_price = myconfig.start_price if last_step is None else ahelper.format_money(last_step.step_price-myconfig.step_margin)
        _step.step_qty = myconfig.unit_qty if last_step is None else last_step.step_qty+myconfig.unit_qty
        _step.price = price
        _step.qty = _step.step_qty
        _step.bs_type = BsType.BUY
        _step.entrust_no = 'history'
        _step.status = EntrustStatus.COMPLETED 
        _step.save()
        last_step = _step
        _qty -= last_step.step_qty
        if _qty-last_step.step_qty<myconfig.unit_qty:
            print('remaining qty=%s' % _qty)

    
    
@click.command()
@click.option('--env', default='dev', help='dev|prod') 
@click.option('--action', default='all', help='data|table|all')
def run(env, action):
    if action in ['table', 'all']:
        create_tabels()
    if action in ['data', 'all']:
        if env=='dev':
            test_data()
        elif env=='prod':
            prod_data()

if __name__ == '__main__':
    Config.PROJECT_PATH = os.getcwd()
    print('PROJECT_PATH=%s' % Config.PROJECT_PATH)
    run()
