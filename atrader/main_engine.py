'''
Created on 2016年3月20日

@author: andy.yang
'''
import os
from logging.handlers import RotatingFileHandler
import logging.config 

from atrader.model.strategy_config import *
from atrader.engine.event_engine import *
from atrader.engine.clock_engine import *
from atrader.engine.quotation_engine import *
from atrader.strategy.astrategy import *
from atrader.constants import *

logging.config.fileConfig(ahelper.get_config_path("logging.conf"))

# create logger     
logger = logging.getLogger(__name__) 

class MainEngine:
    
    def __init__(self, quotation_interval=5):
        event_engine = EventEngine()
        clock_engine = ClockEngine(event_engine)
        configs = StrategyConfig.select_opens()
        logger.debug('Total %s strategy_configs', len(configs))
        stock_codes = [c.stock_code for c in configs]
        quotation_engine = QuotationEngine(event_engine=event_engine, stock_codes=stock_codes, push_interval=quotation_interval)
        
        event_engine.register(EventType.CLOCK, quotation_engine.clock)
        for config in configs:
            _log = ahelper.get_custom_logger('strateger.%s_%s' % (config.stock_code, config.id))
            strategy = AStrategy(event_engine, config, _log)
            logger.info('register strategy as event handler; %s', strategy)
            event_engine.register(EventType.QUOTATION, strategy.run)
            event_engine.register(EventType.CLOCK, strategy.clock)
        
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        self.quotation_engine = quotation_engine
    
    def start(self):
        logger.info("%s start atrader %s", "#"*10, "#"*10)
        if Config.IS_TEST:
            logger.warning("%s TESTING MODE %s", "#"*6, "#"*6)
        self.event_engine.start()
        self.clock_engine.start()
    
    def stop(self):
        logger.info("%s stop atrader %s", "#"*10, "#"*10)
        self.event_engine.stop()
        self.clock_engine.stop()
        self.quotation_engine.stop()
        

if __name__ == '__main__':
    MainEngine().start()
