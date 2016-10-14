'''
Created on 2016年4月29日

@author: andy.yang
'''
import os

class Config(object):
    PROJECT_PATH = os.getcwd()
    IS_TEST = False

class EventType(object):
    CLOCK = 'clock_tick'
    QUOTATION = 'quotation'
    REPORT = 'report'
    ORDER_ENGINE = 'order_engine'
    
class MarketState:
    PRE_OPEN = 'pre_open'
    OPEN = 'open'
    NOON_BREAK = 'noon_break'
    CLOSE = 'close'
    
class BsType(object):
    BUY = 'buy'
    SELL = 'sell'

class EntrustStatus(object):
    OPEN = 1
    COMPLETED = 2
    CANCELED = 3
    
class StrategyStatus(object):
    OPEN = 'open'
    PENDING = 'pending'
    CLOSE = 'close'
    
class StrategyType(object):
    SINGLE = 'single'
    KLINE_WEEK = 'kline_week'

class TradeStatus(object):
    OPEN = 'open'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    
class FixedFlag(object):
    HIGH_STOP = 'high_stop'
    LOW_STOP = 'low_stop'
    SELL_ALL = 'sell_all'
    BUY_ALL = 'buy_all'
    
    