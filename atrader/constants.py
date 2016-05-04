'''
Created on 2016年4月29日

@author: andy.yang
'''
import os

global PROJECT_PATH
PROJECT_PATH = os.getcwd() #'C:\\Users\\andy.yang\\workspace\\atrader'

class EventType(object):
    CLOCK = 'clock_tick'
    QUOTATION = 'quotation'
    
class MarketState:
    OPEN = 'open'
    NOON_BREAK = 'noon_break'
    CLOSE = 'close'
    
class BsType(object):
    BUY = 1
    SELL = 2

class EntrustStatus(object):
    OPEN = 1
    COMPLETED = 2
    CANCELED = 3
    
class StrategyStatus(object):
    NEW = 1
    ACTIVE = 2
    CLOSED = 3