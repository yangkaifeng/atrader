# coding: utf-8
import threading
import logging

from atrader.constants import EventType, MarketState, Config
from atrader.util import ahelper, atime
from atrader.engine.event_engine import Event

logger = logging.getLogger(__name__)

class OrderEngine(object):

    def __init__(self, event_engine, account, interval=1):
        self.lock = threading.Lock()
        self.event_engine = event_engine
        self.is_active = False
        self.interval = interval
        self.account = account
        self.order_codes = {} # {'code':'strategy_id'}

    def start(self):
        self.is_active = True
        self._thread = threading.Thread(target=self.__run)
        self._thread.start()
        logger.info('%s is started', __name__)

    def stop(self):
        self.is_active = False
        logger.info('%s is stopped', __name__)
    
    def handle_event(self, event):
        if self.lock.acquire():
            if event.event_type == EventType.CLOCK:
                self.__clock_handler(event)
            elif event.event_type==EventType.ORDER_ENGINE:
                self.__order_handler(event)
            else:
                self.logger.warning('unhandled event(%s)', event.event_type)
        self.lock.release()
        
    #handle event.type='order_engine    
    def __order_handler(self, event):
        code = event.data['order_code']
        if event.data['action']=='add':
            self.order_codes[code] = event.data['strategy_id']
        elif code in self.order_codes:
            self.order_codes.pop(code)
        logger.debug('%s order_code:%s', event.data['action'], code)
    
    #clock handler
    def __clock_handler(self, event):
        if event.data==MarketState.OPEN:
            if not self.is_active:
                logger.info("market is open, activate the %s", __name__)
                self.start()
        elif event.data==MarketState.NOON_BREAK:
            logger.info("market is in noon break, deactivate the %s", __name__)
            self.stop()
        elif event.data==MarketState.CLOSE:
            logger.info("market is close, deactivate the %s", __name__)
            self.order_codes.clear()
            self.stop()
        else:
            pass
    
    def __pop_code(self, code):
        _id = self.order_codes.pop(code)
        event = Event(event_type=_id, data=code)
        self.event_engine.put(event)
        logger.info('push message: complete strategy(%s) order:%s', event.event_type, event.data)
        if Config.IS_TEST:
            for c in [k for k,v in self.order_codes.items() if v==_id]:
                self.order_codes.pop(c)


    def __run(self):
        while self.is_active:
            if len(self.order_codes)>0:
                ords = self.account.get_orders()
                _codes = [e['order_code'] for e in ords]
                if self.lock.acquire():
                    for c in [k for k in self.order_codes.keys() if k not in _codes]:
                        if c in self.order_codes:
                            self.__pop_code(c)
                self.lock.release()
            atime.sleep(self.interval)

    
