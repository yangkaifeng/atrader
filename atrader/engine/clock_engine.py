# coding: utf-8
import datetime
from threading import Thread

import logging
import time
from constants import EventType as etype, MarketState
from atrader.util import time as atime
from .event_engine import *

logger = logging.getLogger(__name__)

class ClockEngine:
    """时间推送引擎"""
    EventType = etype.CLOCK

    def __init__(self, event_engine):
        self.start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.event_engine = event_engine
        self.is_active = True
        self.clock_engine_thread = Thread(target=self.clocktick)
        self.sleep_time = 1
        self.trading_state = None

    def start(self):
        self.clock_engine_thread.start()
        logger.info('clock_engine is started')

    def clocktick(self):
        min_seconds = 60
        while self.is_active:

            if atime.is_holiday_today():
                pass
            elif atime.is_tradetime_now():  # 工作日，干活了
                if self.trading_state == True:
                    now_time = datetime.datetime.now()
                    time_delta = now_time - self.start_time
                    seconds_delta = int(time_delta.total_seconds())
                    for delta in [0.5, 1, 5, 15, 30, 60]:
                        if seconds_delta % (min_seconds * delta) == 0:
                            self.push_event_type(delta)
                else:
                    self.trading_state = True
                    self.push_event_type(MarketState.OPEN)
            elif self.trading_state is None or self.trading_state == True:
                self.trading_state = False
                if atime.is_noon_break():
                    self.push_event_type(MarketState.NOON_BREAK)
                else:
                    self.push_event_type(MarketState.CLOSE)
            else:
                pass

            time.sleep(self.sleep_time)

    def push_event_type(self, msg):
        event = Event(event_type=self.EventType, data=msg)
        self.event_engine.put(event)
        logger.debug('push clock message: %s', msg)

    def stop(self):
        self.is_active = False
        logger.info('clock_engige is stopped')
