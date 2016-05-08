import datetime
from datetime import timedelta
from functools import lru_cache

import requests

import time 


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
    today = datetime.date.today().strftime('%Y%m%d')
    return is_holiday(today)


def is_tradetime_now():
    now_time = time.localtime()
    now = (now_time.tm_hour, now_time.tm_min, now_time.tm_sec)
    if (9, 30, 0) <= now <= (11, 30, 0) or (13, 0, 0) <= now <= (15, 0, 0):
        return True
    return False


def is_noon_break():
    now_time = time.localtime()
    now = (now_time.tm_hour, now_time.tm_min, now_time.tm_sec)
    return (11, 30, 0) < now < (13, 0, 0)


def calc_next_trade_time_delta_seconds():
    now_time = datetime.datetime.now()
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
