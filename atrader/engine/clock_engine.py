# coding: utf-8
# import datetime
import time
from threading import Thread
import logging

from atrader.constants import EventType as etype, MarketState, Config
from atrader.util import atime
from atrader.engine.event_engine import *

logger = logging.getLogger(__name__)

class ClockEngine:
    """时间推送引擎"""
    EventType = etype.CLOCK

    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.is_active = True
        self.clock_engine_thread = Thread(target=self.clocktick)
        self.sleep_time = 0.01 if Config.IS_TEST else 1
        self.trading_state = None

    def start(self):
        self.clock_engine_thread.start()
        logger.info('clock_engine is started')

    def clocktick(self):
        while self.is_active:
            if atime.is_holiday_today():
                logger.info('today is holiday')
                time.sleep(60*60*6) # sleep for 6 hours
            else:
                state = atime.get_trading_state()
                if self.trading_state!=state:
                    self.push_event_type(state)
                time.sleep(self.sleep_time)

    def push_event_type(self, state):
        event = Event(event_type=self.EventType, data=state)
        self.trading_state = state
        self.event_engine.put(event)
        logger.debug('push clock message: %s', state)

    def stop(self):
        self.is_active = False
        logger.info('clock_engige is stopped')
