# coding: utf-8
from threading import Thread
import easyquotation
import aiohttp
import random
import time
import datetime as _datetime
import logging
import tushare as ts
import sqlalchemy as sqlac
import pandas

from atrader.constants import EventType as etype, MarketState, Config
from atrader.util import ahelper
from atrader.engine.event_engine import *

logger = logging.getLogger(__name__)

class ReportEngine:
    """行情推送引擎基类"""
    EventType = etype.REPORT

    def __init__(self, event_engine, tickets):
        self.event_engine = event_engine
        self.is_active = True
        self.tickets = tickets
        conn_args = ahelper.file2dict(ahelper.get_config_path('database.json'))
        conn_args2 = 'mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8' % (conn_args['user'], conn_args['password'],
                                                              conn_args['host'],conn_args['port'],
                                                              conn_args['database'])
        logger.debug(conn_args2)
        self.conn = sqlac.create_engine(conn_args2)

    def clock(self, event):
        if event.data=='report':
            logger.info("market is report time: prepare data")
            self.update_ticket_data()
            self.gen_report()
        else:
            pass

    
    # ktype: 'D' or 'W'
    def update_ticket_data(self, ktype='D'):
        '''
            date：日期
            open：开盘价
            high：最高价
            close：收盘价
            low：最低价
            volume：成交量
            price_change：价格变动
            p_change：涨跌幅
            ma5：5日均价
            ma10：10日均价
            ma20:20日均价
            v_ma5:5日均量
            v_ma10:10日均量
            v_ma20:20日均量
            turnover:换手率[注：指数无此项]
        '''
        logger.info('update ticket data(ktype=%s) for %s', ktype, self.tickets)
        table = 'ticket_data' if ktype=='D' else 'ticket_data_week'
        for t in self.tickets:
            df1 = pandas.read_sql_query('SELECT date FROM %s WHERE ticket="%s" ORDER BY DATE DESC LIMIT 1' % (table,t), self.conn)
            logger.debug(df1)
            if df1.empty:
                start = '2016-01-01'
            else:
                _date = df1.date.values[0]
                start = (_date+_datetime.timedelta(1)).strftime('%Y-%m-%d')
            logger.debug("start=%s", start)
            
            df = ts.get_hist_data(code=t,start=start,ktype=ktype)
            if not df.empty:
                df['ticket'] = t
                df2 = df.set_index('ticket', append=True)
#                 logger.debug(df2)
                logger.info('add %s records for %s', df.index.size, t)
                df2.to_sql(table, self.conn, if_exists='append',
                           dtype={'date': sqlac.types.Date,'ticket':sqlac.types.String(length=10)})
            else:
                logger.info('no data since %s for %s', start, t)
            
    def gen_report(self):
        pass
    
    
def is_holiday(date):
    df = ts.trade_cal()
    holiday = df[df.isOpen == 0]['calendarDate'].values
    
    if isinstance(date, str):
        today = _datetime.datetime.strptime(date, '%Y-%m-%d')
        today2 = '%s/%s/%s' % (today.year, today.month, today.day)
    if today.isoweekday() in [6, 7] or today2 in holiday:
        return True
    else:
        return False
        
if __name__ == '__main__':
    Config.PROJECT_PATH = '..\\..\\'
    logger = logging.getLogger('atrader.engine.report')
    logging.config.fileConfig("..\\..\\config\\logging.conf")
    eng = ReportEngine(event_engine=None,tickets=['600009'])
    eng.update_ticket_data(ktype='W')  
#     logger.debug(is_holiday('2016-6-9'))  
#     logger.debug(is_holiday('2016-6-10'))   
#     logger.debug(is_holiday('2016-9-14'))  
#     logger.debug(is_holiday('2016-9-15'))   
#         
