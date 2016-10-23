'''
Created on 2016年4月29日

@author: andy.yang
'''
from peewee import *
# import datetime as _datetime
import logging
import threading
import tushare as ts
# import sqlalchemy as sqlac
import pandas

from atrader.constants import *
from atrader.model.base_model import *
from atrader.model.trade_step import TradeStep
from atrader.model.trade_order import TradeOrder
from atrader.model.strategy_detail import StrategyDetail
from atrader.strategy.base_strategy import BaseStrategy
from atrader.account import Account
from atrader.account import NotLoginException
from atrader.util import ahelper,atime
from atrader.engine.event_engine import Event
from atrader.constants import Config
from atrader.dummy_quotation_server import DummyQuotationServer
from constants import BsType
from pygments.lexers._mql_builtins import c_types
import code




class StrategyB(object):
    name = 'StrategyB'
    
    def __init__(self, event_engine, clock_engine, strategy, interval=1):
        self.logger = ahelper.get_custom_logger('strateger.%s_%s' % (strategy.symbol, strategy.id))
        self.logger.info('__init__: %s(id=%s)', self.name, strategy.id)
        self._thread = threading.Thread(target=self.__run)
        self.is_started = False
        self.completed_code = None
        self.interval = interval
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        self.market_state = None
        self.strategy = strategy        
        self.lock = threading.Lock()
        self.is_pending_close = False
        self.account = Account(self.strategy.account_code)        
        self.open_steps = {} #{'order_code':[step list]}
        self.last_step = None
        self.strategy_detail = None
        self.lot_available = 0 
        self.cash_available = self.strategy.budget 
        self.price_limit_up = 0
        self.price_limit_down = 0
        
        details = StrategyDetail.select_open(strategy.id)
        if len(details)==0:
            self.logger.info('__init__: create new strategy_detail')
            self.__new_strategy_detail(is_init=True)
        elif len(details)>1:
            raise Exception('__init__: UNEXPECTED - more than one open strategy details of strategy(id=%s)' % strategy.id)
        else:
            self.strategy_detail = details[0]
            self.logger.info('__init__: load existing strategy_detail(id=%s)', self.strategy_detail.id)
            self.cash_available = self.strategy_detail.init_cash+TradeOrder.calc_revenue(self.strategy_detail.id)
            self.lot_available = TradeOrder.calc_end_qty(self.strategy_detail.id)
            self.last_step = TradeStep.select_last(self.strategy_detail.id)
            _day = atime.now().day
            for s in TradeStep.select_open(self.strategy_detail.id):
                if s.created_at.day != _day:#cancel old steps
                    s.status = TradeStatus.CANCELED
                    s.updated_at = atime.now()
                    s.save() 
                else:
#                     self.event_engine.put(Event(event_type=EventType.ORDER_ENGINE, data={'order_code':s.order_code, 'strategy_id':self.strategy.id, 'action':'add'}))
                    if s.order_code in self.open_steps:
                        self.open_steps[s.order_code].append(s)
                    else:
                        self.open_steps[s.order_code]=[s]
        self.logger.info('__init__: cash_available=%s, lot_available=%s',self.cash_available,self.lot_available)
    
    def start(self):
        if not self.is_started:
            self.is_started = True        
            self._thread.start()
            self.logger.info('%s is started', __name__)

    def stop(self):
        self.is_started = False
        self.logger.info('%s is stopped', __name__)
        
    def __run(self):
        while self.is_started:
            if self.completed_code!=None:
                if self.completed_code in self.open_steps:
                    self.logger.info('__run: deal with completed order_code(%s)', self.completed_code)
                    self.__complete_order(self.completed_code)
                    self.__cancel_order()
                    if self.is_pending_close:
                        self.__new_strategy_detail()
                    else:
                        self.__place_order()
                else:
                    self.logger.warn('__run: UNEXPECTED - no order(%s) in open_steps: %s', self.completed_code, list(self.open_steps.keys()))
                self.completed_code = None
                
            if self.clock_engine.market_state!=self.market_state:
                self.market_state=self.clock_engine.market_state
                if self.market_state in (MarketState.OPEN, MarketState.PRE_OPEN):
                    self.logger.info("__run: market is %s - place orders", self.market_state)
                    if self.strategy_detail:
                        self.cash_available = self.strategy_detail.init_cash+TradeOrder.calc_revenue(self.strategy_detail.id)
                        self.lot_available = TradeOrder.calc_end_qty(self.strategy_detail.id)
                        self.logger.info('__run: cash_available=%s, lot_available=%s',self.cash_available,self.lot_available)
                    else:
                        self.__new_strategy_detail()
                    if self.strategy_detail:
                        self.__place_order()
                elif self.market_state==MarketState.CLOSE:
                    self.logger.info("__run: market is close - cancel orders")
                    self.__cancel_order()
                        
            atime.sleep(self.interval)
            
            
    def handle_event(self, event):
        self.logger.info('handle_event: event_type=%s, data=%s', event.event_type, event.data)
        if event.event_type==self.strategy.id:
            self.completed_code = event.data
        else:
            self.logger.warning('unhandled event(%s)', event.event_type)

    
    # create strategy_detail
    def __new_strategy_detail(self, is_init=False):
        self.open_steps.clear()
        self.last_step = None
        init_cash = self.strategy.budget
        #close old strategy_detail
        if self.strategy_detail: 
            self.logger.info('__new_strategy_detail: close old strategy_detail(id=%s)', self.strategy_detail.id)
            remaining_qty = TradeOrder.calc_end_qty(self.strategy_detail.id, include_today=True)
            if remaining_qty>0:
                self.logger.warning('__new_strategy_detail: cannot close old strategy_detail cause remaining_qty=%s', remaining_qty)
                return
            self.strategy_detail.end_cash = ahelper.format_money(self.strategy_detail.init_cash+TradeOrder.calc_revenue(self.strategy_detail.id))
            self.strategy_detail.is_active = False
            self.strategy_detail.updated_at = atime.now()
            self.strategy_detail.save()
            self.is_pending_close=False
            init_cash = self.strategy_detail.end_cash
            self.strategy_detail = None
            #stop this strategy
            actual_loss = self.strategy.budget-init_cash
            if self.strategy.type==StrategyType.SINGLE or actual_loss >=self.strategy.fix_loss:
                self.logger.info('__new_strategy_detail: close strategy(actual_loss=%s, allowed_loss=%s)', actual_loss, self.strategy.fix_loss)
                self.__close_strategy()
                return
            
        if not is_init and atime.today().weekday()>0:
            self.logger.info('__new_strategy_detail: Only Monday we can recreate new strategy_detail')
            return
            
        #create new strategy detail
        _start = atime.date2str(atime.calc_date(atime.today(), -30))
        _end = atime.date2str(atime.today())
        df = ts.get_hist_data(code=self.strategy.symbol,start=_start,end=_end,ktype='W')
        top_price = ahelper.format_money(df[0:2]['high'].max())
        bottom_price = ahelper.format_money(df[0:2]['low'].min())
        _count = min(int((top_price-bottom_price)//(top_price*0.01)),self.strategy.param2)
        step_delta_price = ahelper.format_money((top_price-bottom_price)/_count)
        _tmp = sum([(bottom_price+(_count-n)*step_delta_price)*(1+(n-1)*self.strategy.param1) for n in range(1,_count+1)])
        init_qty = int(init_cash/_tmp//100*100)
        _total_qty = sum([(1+(n-1)*self.strategy.param1)*init_qty for n in range(1,_count+1)])
        start_price = ahelper.format_money(init_qty*_tmp/_total_qty)
        new_sd = StrategyDetail(strategy=self.strategy,
                                top_price = top_price,
                                bottom_price = bottom_price,
                                start_price=start_price,
                                step_delta_price=step_delta_price,
                                step_count=_count+1,
                                init_qty=init_qty,
                                step_delta_qty=int(init_qty*self.strategy.param1),
                                high_stop_ratio=0.025,
                                low_stop_ratio=0.025,
                                init_cash=init_cash
                                )
        new_sd.save()
        self.logger.info('__new_strategy_detail: created new strategy_detail(id=%s)', new_sd.id)
        self.strategy_detail = new_sd
        self.lot_available = 0 
        self.cash_available = init_cash
    
    
    
    #stop the strategy
    def __close_strategy(self):
        self.logger.info('__close_strategy: close strategy and unregister all events with it')
        self.strategy.status = StrategyStatus.CLOSE
        self.strategy.updated_at = atime.now()
        self.strategy.save()
        self.event_engine.unregister(EventType.CLOCK, self.handle_event)
        self.event_engine.unregister(self.strategy.id, self.handle_event)
    
    
    #place orders
    def __place_order(self):
        if self.open_steps:
            self.logger.info('__place_order: Not place order - existing open_steps: %s', self.open_steps)
            return
        
        stock_data = self.account.get_real_stocks([self.strategy.symbol])
        _close = stock_data[self.strategy.symbol]['close']
        self.price_limit_down = ahelper.format_money(_close*0.9)
        self.price_limit_up = ahelper.format_money(_close*1.1)
        c_price = stock_data[self.strategy.symbol]['now']
        _no = self.strategy_detail.step_no(c_price)
        
        self.logger.info('__place_order: _no=%s, c_price=%s, last_step=%s', _no, c_price, self.last_step)
        if _no==FixedFlag.BUY_ALL:
            self.__new_open_steps(self.strategy_detail.step_count-1, c_price)
        elif _no==FixedFlag.SELL_ALL:
            self.__new_open_steps(0, c_price)
        elif _no in (FixedFlag.HIGH_STOP, FixedFlag.LOW_STOP):
            self.__new_open_steps(0, c_price)#sell all
            if self.open_steps:
                self.is_pending_close = True
            else:
                self.__new_strategy_detail()
        elif self.last_step is None:
            m_price = min(c_price, self.strategy_detail.start_price)
            self.__new_open_steps(self.strategy_detail.step_no(m_price), m_price)
        elif self.last_step.step_no-_no>1:
            #sell
            self.__new_open_steps(_no+1, c_price)
            #buy
            self.__new_open_steps(self.last_step.step_no+1, self.strategy_detail.step_price(self.last_step.step_no+1))
        elif _no-self.last_step.step_no>=1:
            #buy
            self.__new_open_steps(_no, c_price)
            #sell
            if self.last_step.step_no>0:
                self.__new_open_steps(self.last_step.step_no-1, self.strategy_detail.step_price(self.last_step.step_no-1))
        elif _no==self.last_step.step_no:
            if _no>0:
                self.__new_open_steps(_no-1, self.strategy_detail.step_price(_no-1))
            self.__new_open_steps(_no+1, self.strategy_detail.step_price(_no+1))
        elif self.last_step.step_no-_no==1:
            self.__new_open_steps(_no, self.strategy_detail.step_price(_no))
            self.__new_open_steps(_no+2, self.strategy_detail.step_price(_no+2))
                
    
      
    def __new_open_steps(self, _no, _price):
        self.logger.info('__new_open_steps: prepare open steps for (step_no=%s, price=%s)', _no, _price)
        _steps = []
        last_step = self.last_step
        no_list = []
        c_type = None
        
        if last_step is None:
            c_type = BsType.BUY
            no_list = list(range(1, _no+1))
        elif _no>last_step.step_no:
            c_type = BsType.BUY 
            no_list = list(range(last_step.step_no+1, _no+1))
        elif _no<last_step.step_no:
            c_type = BsType.SELL
            no_list = list(range(_no,last_step.step_no))
            no_list.reverse()
           
        self.logger.info("__new_open_steps: c_type=%s, no_list=%s", c_type, no_list) 
        
        lot_available = self.lot_available
        for n in no_list:
            if last_step is None:
                qty = self.strategy_detail.init_qty
                source = last_step
            elif last_step.source is None:
                self.logger.info("__new_open_steps: normal step - link to the first step")
                qty = last_step.step_qty+self.strategy_detail.step_delta_qty if last_step.bs_type==c_type else self.strategy_detail.init_qty
                source = last_step
            elif last_step.step_no==0:
                if c_type==BsType.BUY:
                    self.logger.info("__new_open_steps: special step - start a new loop!")
                    qty = self.strategy_detail.init_qty
                    source = None
                else:
                    raise Exception('__new_open_steps: UNEXPECTED - cannot sell stocks after last_step.step_no==0')
            elif last_step.step_qty==last_step.source.step_qty:
                self.logger.info("__new_open_steps: special step - zero cleaning the last step chain! ")
                ss_step = last_step.source if last_step.source.source is None else last_step.source.source
                if last_step.bs_type==c_type:
                    qty = ss_step.step_qty+self.strategy_detail.step_delta_qty
                    source = ss_step.source
                else:
                    qty = self.strategy_detail.init_qty
                    source = ss_step
            else:
                if last_step.bs_type==c_type:
                    qty = last_step.step_qty+self.strategy_detail.step_delta_qty
                    source = last_step.source
                else:
                    qty = self.strategy_detail.init_qty
                    source = last_step
                self.logger.info("__new_open_steps: normal step - %s qty=%s", c_type, qty)
            if c_type==BsType.SELL:
                if qty<=lot_available:
                    lot_available = lot_available-qty
                else:
                    self.logger.info('__new_open_steps: no enough lot, sell qty=%s while lot_available=%s', qty, lot_available)
                    break
            _step = TradeStep(source=source,
                              step_no=n,
                              step_qty=qty,
                              step_price=self.strategy_detail.step_price(n),
                              price=_price,
                              bs_type=c_type,
                              status=TradeStatus.OPEN,
                              strategy_detail=self.strategy_detail)
            _steps.append(_step)
            last_step = _step
            
        self.__buy_or_sell(_steps)
            
    @db.atomic()
    def __buy_or_sell(self, steps):
        #check conditions to place order
        if steps==[]: 
            return
        price = steps[-1].price
        if price<self.price_limit_down or price>self.price_limit_up:
            self.logger.warning('__buy_or_sell: CANNOT PLACE ORDER BECAUSE PRICE(%s) IS NOT BETWEEN PRICE LIMIT(%s, %s)', price, self.price_limit_down, self.price_limit_up)
            return 
        bs_type = steps[-1].bs_type
        qty = sum([e.step_qty for e in steps])
        if bs_type==BsType.SELL and qty>self.lot_available:
            self.logger.warning('__buy_or_sell: CANNOT PLACE ORDER BECAUSE no enough lot: actual %s but require %s', self.lot_available, qty)
            return
        elif bs_type==BsType.BUY and qty*price>self.cash_available:
            self.logger.warning('__buy_or_sell: CANNOT PLACE ORDER BECAUSE no enough budget: actual %s but require %s', self.cash_available, qty*price)
            return
        
        self.logger.info('__buy_or_sell: %s', steps)
        code = self.account.buy_or_sell(bs_type, self.strategy.symbol, price, qty)
        for s in steps:
            s.order_code = code
            s.qty = s.step_qty
            s.save()
        self.open_steps[code] = steps
     
    
    @db.atomic()
    def __complete_order(self, order_code):
        self.logger.info('__complete_order: order_code=%s', order_code)
        steps = self.open_steps.pop(order_code)
        TradeStep.update_status(order_code, TradeStatus.COMPLETED)
        self.last_step = steps[-1]
        #save trade order
        self.__save_trade_order(order_code, self.last_step.price, sum([s.qty for s in steps]), self.last_step.bs_type)
        
        
    @db.atomic()             
    def __cancel_order(self):
        self.logger.info('__cancel_order: order_code in %s', self.open_steps.keys())
        for code,_steps in self.open_steps.items():
            self.logger.info('__cancel_order: check order(%s) before canceling', code)
            e = self.account.get_order(code)
            self.logger.info('__cancel_order: get_order(%s) ', code)
            self.account.cancel_order(code)
            self.logger.info('__cancel_order: cancel_order(%s) ', code)
#             self.event_engine.put(Event(event_type=EventType.ORDER_ENGINE, data={'order_code':code, 'strategy_id':self.strategy.id, 'action':'delete'}))
            actual_qty = e['actual_qty'] if e else 0 #deal with the partial completed case
            if actual_qty==0:
                TradeStep.update_status(code, TradeStatus.CANCELED)
            else:
                for p in _steps:
                    if p.step_qty <= actual_qty:
                        actual_qty -= p.step_qty
                        p.status = TradeStatus.COMPLETED
                    elif 0 < actual_qty < p.step_qty:
                        p.qty = actual_qty #part completed
                        p.status = TradeStatus.COMPLETED
                        actual_qty = 0
                    else:
                        p.status = TradeStatus.CANCELED # canceled
                    p.updated_at = atime.now()
                    p.save()
                    if p.status==TradeStatus.COMPLETED:
                        self.last_step = p
                
                #save trade order
                self.__save_trade_order(code, self.last_step.price, actual_qty, self.last_step.bs_type)
        
        #clear open_steps
        self.open_steps.clear()
        self.logger.debug('__cancel_order: clear open_steps-%s', self.open_steps.keys())
        
    
    def __save_trade_order(self, code, price, qty, bs_type):
        self.logger.info('__save_trade_order: code=%s, %s qty=%s, price=%s', code, bs_type, qty, price)
        order = TradeOrder(strategy_detail=self.strategy_detail,
                           order_code=code,
                           price=price,
                           qty=qty,
                           bs_type=bs_type)
        order.calc_fee()
        order.save()
        if bs_type==BsType.BUY:
            self.cash_available = ahelper.format_money(self.cash_available - order.fee - order.qty*order.price)
        else:
            self.cash_available = ahelper.format_money(self.cash_available - order.fee + order.qty*order.price)
            self.lot_available = self.lot_available-order.qty
        self.logger.info('__save_trade_order: cash_available=%s, lot_available=%s',self.cash_available,self.lot_available)
            
