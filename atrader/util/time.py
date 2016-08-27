import datetime
from datetime import timedelta
from functools import lru_cache

import requests
import time 

from atrader.constants import Config
from atrader.dummy_quotation_server import DummyQuotationServer

def today():
    if Config.IS_TEST:
        _dt = DummyQuotationServer().date()
        return datetime.date(_dt.year,_dt.month, _dt.day)
    else:
        return datetime.date.today()

def localtime():
    if Config.IS_TEST:
        return now().timetuple()
    else:
        return time.localtime()

def now():
    if Config.IS_TEST:
        _dt = DummyQuotationServer().date()
        return datetime.datetime.now().replace(year=_dt.year,month=_dt.month,day=_dt.day,hour=_dt.hour)
    else:
        return datetime.datetime.now()
 
def sleep(seconds):
    if Config.IS_TEST:
        time.sleep(seconds*0.2)
    else:
        time.sleep(seconds)
     
        
@lru_cache()
def is_holiday(day):
    weekday = datetime.datetime.strptime(day, '%Y%m%d').isoweekday()
    return weekday>5 #TODO - implement the legal holiday
#     api = 'http://www.easybots.cn/api/holiday.php'
#     params = {'d': day}
#     rep = requests.get(api, params)
#     res = rep.json()[day if isinstance(day, str) else day[0]]
#     return True if res == "1" else False

def is_holiday_today():
    td = today().strftime('%Y%m%d')
    return is_holiday(td)


def is_tradetime_now():
    now_time = localtime()
    now = (now_time.tm_hour, now_time.tm_min, now_time.tm_sec)
    if (9, 30, 0) <= now <= (11, 30, 0) or (13, 0, 0) <= now <= (15, 0, 0):
        return True
    return False


def is_noon_break():
    now_time = localtime()
    now = (now_time.tm_hour, now_time.tm_min, now_time.tm_sec)
    return (11, 30, 0) < now < (13, 0, 0)


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
