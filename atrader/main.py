'''
Created on 2016年3月20日

@author: andy.yang
'''
import os
from logging.handlers import RotatingFileHandler
import logging.config 


from model.strategy_config import *
from engine.event_engine import *
from engine.clock_engine import *
from engine.quotation_engine import *
from strategy.astrategy import *
from constants import *

IS_TEST = True
logging.config.fileConfig("config\\logging.conf")

# create logger     
logger = logging.getLogger(__name__) 

def main():
    event_engine = EventEngine()
    clock_engine = ClockEngine(event_engine)
    configs = StrategyConfig.select_opens()
    logger.debug('Total %s strategy_configs', len(configs))
    stock_codes = [c.stock_code for c in configs]
    quotation_engine = QuotationEngine(event_engine=event_engine, stock_codes=stock_codes, push_interval=1)
    
    event_engine.register(EventType.CLOCK, quotation_engine.clock)
    for config in configs:
        strategy = AStrategy(event_engine, config, get_strategy_logger('%s_%s' % (config.stock_code, config.id)))
        logger.info('register strategy as event handler; %s', strategy)
        event_engine.register(EventType.QUOTATION, strategy.run)
        event_engine.register(EventType.CLOCK, strategy.clock)
    
    event_engine.start()
#     quotation_engine.start()
    clock_engine.start()

def get_strategy_logger(name):
    _logger = logging.getLogger('strateger.%s' % name)
    file_name = os.path.join(os.getcwd(), '..', 'log', 'strategy_'+name+'.log')
    
    handler = RotatingFileHandler(file_name, 
                                  maxBytes=10*1024*1024,backupCount=5)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(thread)d - %(name)s - %(levelname)s:   %(message)s')
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    logger.debug('strategy logger file: %s, log_level:%s', file_name, _logger.level)
    return _logger

if __name__ == '__main__':
    logger.info("%s start atrader %s", "#"*10, "#"*10)
    main()
