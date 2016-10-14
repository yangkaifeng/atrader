# coding: utf-8
from threading import Thread
import easyquotation
import aiohttp
import random
# import time
import logging

from atrader.constants import EventType as etype, MarketState, Config
from atrader.util import ahelper, atime
from atrader.engine.event_engine import *
from atrader.dummy_quotation_server import DummyQuotationServer

logger = logging.getLogger(__name__)

class QuotationEngine:
    """行情推送引擎基类"""
    EventType = etype.QUOTATION

    def __init__(self, event_engine, stock_codes, push_interval=1):
        self.event_engine = event_engine
        self.is_active = True
        
        self.source = easyquotation.use("lf")
        self.stock_codes = stock_codes
        self.push_interval = push_interval

    def start(self):
        self.is_active = True
        self.quotation_thread = Thread(target=self.push_quotation)
        self.quotation_thread.start()
        logger.info('quotation_engige is started')

    def stop(self):
        self.is_active = False
        logger.info('quotation_engige is stopped')
        
    def clock(self, event):
        if event.data==MarketState.OPEN:
            logger.info("market is open, activate the quotation_engine")
            self.start()
        elif event.data==MarketState.NOON_BREAK:
            logger.info("market is in noon break, deactivate the quoation_engine")
            self.stop()
        elif event.data==MarketState.CLOSE:
            logger.info("market is close, deactivate the quoation_engine")
            self.stop()
        else:
            pass

    def push_quotation(self):
        while self.is_active:
            try:
                response_data = self.fetch_quotation()
            except aiohttp.errors.ServerDisconnectedError as _error:
                logger.warn('http connection error: %s', format(_error))
                atime.sleep(self.push_interval)
                continue
            event = Event(event_type=self.EventType, data=response_data)
            self.event_engine.put(event)
            logger.info('push %s message: %s', event.event_type, event.data)
            atime.sleep(self.push_interval)

    def fetch_quotation(self):
        if Config.IS_TEST:
            _dict = dict()
            for s in self.stock_codes:
                p = ahelper.format_money(DummyQuotationServer(s).price())
                _dict[s] =  {"now":p,"ask1":p+0.01, "bid1":p-0.01}
            return _dict
        else:
            _data = self.source.stocks(self.stock_codes)
            _dict = dict()
            for s in self.stock_codes:
                _dict[s] =  {"now":_data[s]["now"]}
            return _dict
