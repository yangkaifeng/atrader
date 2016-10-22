'''
Created on 2016年3月20日

@author: andy.yang
'''
import os
from logging.handlers import RotatingFileHandler
import logging.config 

from atrader.model.strategy_config import StrategyConfig
from atrader.model.strategy import Strategy
from atrader.engine.event_engine import *
from atrader.engine.clock_engine import *
from atrader.engine.quotation_engine import *
from atrader.strategy.strategy_a import StrategyA
from atrader.strategy.strategy_b import StrategyB
from atrader.constants import *
from atrader.engine.order_engine import OrderEngine
from atrader.account import Account
from atrader.dummy_quotation_server import DummyQuotationServer

logging.config.fileConfig(ahelper.get_config_path("logging.conf"))

# create logger     
logger = logging.getLogger(__name__) 

class MainEngine:
    
    def __init__(self, quotation_interval=5):
        event_engine = EventEngine()
        clock_engine = ClockEngine(event_engine)
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        
#         configs = StrategyConfig.select_opens()
#         logger.debug('Total %s strategy_configs', len(configs))
#         stock_codes = [c.stock_code for c in configs]
#         quotation_engine = QuotationEngine(event_engine=event_engine, stock_codes=stock_codes, push_interval=quotation_interval)
#         event_engine.register(EventType.CLOCK, quotation_engine.clock)
#         self.quotation_engine = quotation_engine
#         for config in configs:
#             a = StrategyA(event_engine, config)
#             logger.info('register strategy as event handler; %s', a)
#             event_engine.register(EventType.QUOTATION, a.run)
#             event_engine.register(EventType.CLOCK, a.clock)
        
        strategies = Strategy.select_opens()
        sbs = []
        for s in strategies:
            b = StrategyB(event_engine,clock_engine,s)
            sbs.append(b)
            logger.info('__init__: register strategy(id=%s)', s.id)
            event_engine.register(s.id, b.handle_event)
#             event_engine.register(EventType.CLOCK, b.handle_event)            
        self.sbs = sbs
        
    
    def start(self):
        logger.info("%s start atrader %s", "#"*10, "#"*10)
        if Config.IS_TEST:
            logger.warning("%s TESTING MODE %s", "#"*6, "#"*6)
            dummy_server = DummyQuotationServer()
            dummy_server.init(list(set([s.strategy.symbol for s in self.sbs])), self.sbs)
            dummy_server.start1()
        self.event_engine.start()
        self.clock_engine.start()
        for code in list(set([s.strategy.account_code for s in self.sbs])):
            sbs = [b for b in self.sbs if b.strategy.account_code==code]
            order_engine = OrderEngine(self.event_engine,self.clock_engine, Account(code),sbs)
#             self.event_engine.register(EventType.CLOCK, order_engine.handle_event)
#             self.event_engine.register(EventType.ORDER_ENGINE, order_engine.handle_event)
            order_engine.start()
        
        for sb in self.sbs:
            sb.start()
    
    def stop(self):
        logger.info("%s stop atrader %s", "#"*10, "#"*10)
        self.event_engine.stop()
        self.clock_engine.stop()
#         self.quotation_engine.stop()
        

if __name__ == '__main__':
    MainEngine().start()
