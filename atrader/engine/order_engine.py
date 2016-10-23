# coding: utf-8
import threading
import logging

from atrader.constants import EventType, MarketState, Config
from atrader.util import ahelper, atime
from atrader.engine.event_engine import Event

logger = logging.getLogger(__name__)

class OrderEngine(object):

    def __init__(self, event_engine, clock_engine, account, sbs, interval=1):
        self.lock = threading.Lock()
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        self.is_started = False
        self.is_active = False
        self._thread = threading.Thread(target=self.__run)
        self.interval = interval
        self.account = account
        self.sbs = sbs
        self.completed_orders = []
        self.market_state = None


    def start(self):
        if not self.is_started:
            self.is_started = True        
            self._thread.start()
            logger.info('%s is started', __name__)

    def stop(self):
        self.is_started = False
        logger.info('%s is stopped', __name__)


    def __run(self):
        while self.is_started:
            if self.clock_engine.market_state!=self.market_state:
                self.market_state=self.clock_engine.market_state
                if self.market_state==MarketState.CLOSE:
                    self.completed_orders.clear()
                    
            if self.market_state==MarketState.OPEN and self.sbs:
                #TODO- open_steps is changing
                all_codes = {}
                for sb in self.sbs:
                    for c in sb.open_steps:
                        all_codes[c] = sb.strategy.id
                open_codes = [e['order_code'] for e in self.account.get_orders()]
                logger.debug('__run: checl all orders - %s', all_codes)
                for code,sid in all_codes.items():
                    if (code not in self.completed_orders) and (code not in open_codes):
                        event = Event(event_type=sid, data=code)
                        self.event_engine.put(event)
                        self.completed_orders.append(code)
                        logger.info('push message: complete order of strategy(id=%s): %s', event.event_type, event.data)
                    
            atime.sleep(self.interval)
            

    
