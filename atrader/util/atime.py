import datetime
from datetime import timedelta
from functools import lru_cache
import tushare as ts
import logging
import requests
import time 

from atrader.constants import Config,MarketState
from atrader.dummy_quotation_server import DummyQuotationServer

logger = logging.getLogger(__name__)

def today():
    if Config.IS_TEST:
        return DummyQuotationServer().now().date()
    else:
        return datetime.date.today()


def now():
    if Config.IS_TEST:
        return DummyQuotationServer().now()
    else:
        return datetime.datetime.now()
 
def sleep(seconds):
    if Config.IS_TEST:
        time.sleep(seconds*0.01)
    else:
        time.sleep(seconds)

def calc_date(date, days):
    return date+datetime.timedelta(days=days)     

def date2str(date,fmt='%Y-%m-%d'):
    return datetime.datetime.strftime(date, fmt)
        
@lru_cache()
def is_holiday(date):
    str_date = '%s/%s/%s' % (date.year, date.month, date.day)
    df = ts.trade_cal()
    holidays = df[df.isOpen == 0]['calendarDate'].values
    return str_date in holidays
    

def is_holiday_today():
    return is_holiday(today())


def get_trading_state():
    now_time = now()
    _now = (now_time.hour, now_time.minute, now_time.second)
    if _now < (8, 0, 0) or _now > (15,0,0):
        return MarketState.CLOSE
    elif (8, 0, 0) <= _now < (9, 30, 0):
        return MarketState.PRE_OPEN
    elif (11, 30, 0) < _now < (13, 0, 0):
        return MarketState.NOON_BREAK
    else:
        return MarketState.OPEN
        
def calc_next_trade_time_delta_seconds():
    now_time = now()
    now = (now_time.hour, now_time.minute, now_time.second)
    if now < (9, 30, 0):
        next_trade_start = now_time.replace(hour=9, minute=30, second=0, microsecond=0)
    elif (12, 0, 0) < now < (13, 0, 0):
        next_trade_start = now_time.replace(hour=13, minute=0, second=0, microsecond=0)
    elif now > (15, 0, 0):
        distance_next_work_day = 1
        while True:
            target_day = now_time + timedelta(days=distance_next_work_day)
            if is_holiday(target_day.strftime('%Y%m%d')):
                distance_next_work_day += 1
            else:
                break

        day_delta = timedelta(days=distance_next_work_day)
        next_trade_start = (now_time + day_delta).replace(hour=9, minute=30,
                                                          second=0, microsecond=0)
    else:
        return 0
    time_delta = next_trade_start - now_time
    return time_delta.total_seconds()
