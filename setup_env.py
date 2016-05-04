'''
Created on 2016年4月30日

@author: andy.yang
'''
import os
from peewee import *
import click

from atrader.constants import PROJECT_PATH
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
    create_tabels()
    ss = [StrategyConfig(account_code='666623491888', stock_code='000400', unit_qty=200, total_num=8, 
                        start_price=15.87, step_ratio=0.0162, low_stop_ratio=0.1, high_stop_ratio=0.1, status=2)]
    for s in ss:
        s.save()
    print('insert %s' % ss)
    
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
    global PRJECT_PATH
    PROJECT_PATH = os.getcwd()
    print('PROJECT_PATH=%s' % PROJECT_PATH)
    run()
