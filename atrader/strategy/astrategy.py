'''
Created on 2016年4月29日

@author: andy.yang
'''
from peewee import *
import datetime as _datetime
import logging
import threading

from atrader.constants import *
from atrader.model.base_model import *
from atrader.model.strategy_config import * 
from atrader.model.step_position import *
from atrader.strategy.base_strategy import BaseStrategy
from atrader.account import Account
from atrader.strategy import astrategy
from atrader.account import NotLoginException




class AStrategy(BaseStrategy):
    name = 'AStrategy'
    
    def init(self):
        self.lock = threading.Lock()
        self.is_active = False
        self.account = Account(self.strategy_config.account_code, self.is_test)
        self.logger.debug('init AStrategy')
    
    def clock(self, event):
        if event.data==MarketState.OPEN:
            self.logger.info("market is open")
            self.is_active = True
        elif event.data==MarketState.NOON_BREAK:
            self.logger.info("market is in noon break")
            self.is_active = False
        elif event.data==MarketState.CLOSE:
            self.logger.info("market is close")
            if self.lock.acquire():
                self.is_active = False
                if self.strategy_config.open_steps:
                    self.logger.info('cancel open entrust when market is closed')
                    self.__cancel_entrust()
                self.lock.release()
        else:
            pass
    
    def strategy(self, event):
        try:
            if self.lock.acquire():
                if self.is_active:
                    c_price = event.data[self.strategy_config.stock_code]["now"]
                    
                    if self.strategy_config.open_steps:
                        _p0 = self.strategy_config.open_steps[-1].step_price
                    elif self.strategy_config.completed_steps:
                        _p0 = self.strategy_config.completed_steps[-1].step_price
                    else:
                        _p0 = self.strategy_config.start_price+self.strategy_config.step_margin
                    
                    _p1 = ahelper.format_money(self.strategy_config.start_price-self.strategy_config.total_num*self.strategy_config.step_margin)
                    _p2 = ahelper.format_money(_p0-self.strategy_config.step_margin)
                    _p3 = ahelper.format_money(_p0+self.strategy_config.step_margin)
                    _p4 = ahelper.format_money(self.strategy_config.start_price+self.strategy_config.step_margin)
                    self.logger.info("check %s:%s in %s-[%s,%s]-[%s-%s]-%s", 
                                      self.strategy_config.stock_code, c_price, 
                                      self.strategy_config.low_stop_price, _p1, _p2, _p3, _p4, self.strategy_config.high_stop_price)
                    
                    return_code = self.__think(c_price)
                    
                    if return_code==100: #continue
                        self.logger.debug("continue to do the strategy immediately")
                        self.lock.release()
                        self.strategy(event)
                    elif return_code==300: #close the strategy
                        self.logger.info("close the strategy right now")
                        self.logger.info("set strategy.status to close")
                        self.strategy_config.status=StrategyStatus.CLOSED
                        self.strategy_config.updated_at = _datetime.datetime.now()
                        self.strategy_config.save()
                        self.logger.info("remove the strategy from event_engine")
                        self.event_engine.unregister(EventType.QUOTATION, self.run)
                        self.event_engine.unregister(EventType.CLOCK, self.clock)
                        self.is_active = False
                    else:
                        pass
        except NotLoginException:
            self.logger.warn('catch the NotLoginException')
            self.account.autologin()
        finally:
            try:
                self.lock.release()
            except:
                self.logger.error('release unlocked lock')
                pass
        
    
    def __think(self, c_price):
        '''
        check entrust orders first
        get latest stock price
        think actions 
        return {"code":100/200/300,"bs_type":1 or 2, "price":price, "qty":qty}
        '''
        dif_no = int(abs(self.strategy_config.start_price-c_price)//self.strategy_config.step_margin)
        self.logger.debug("current price: %s, dif_no:%s", c_price, dif_no)
        return_code = 200
        
        if self.strategy_config.open_steps:
            self.logger.debug("already have an entrust")
            return_code = self.__check_entrust(c_price)
        elif self.strategy_config.completed_steps==[]:
            
            if self.strategy_config.low_stop_price < c_price <=self.strategy_config.start_price: #buy first position 
                self.logger.info("new first batch of positions")
                for no in range(1,dif_no+2):
                    start_pos = self.strategy_config.open_steps[0] if self.strategy_config.open_steps else None
                    s_price = ahelper.format_money(self.strategy_config.start_price-(no-1)*self.strategy_config.step_margin)
                    self.strategy_config.open_steps.append(StepPosition(source=start_pos, step_no=no, step_price=s_price, step_qty=no*self.strategy_config.unit_qty, 
                                                        price=c_price, bs_type=BsType.BUY, status=EntrustStatus.OPEN, strategy=self.strategy_config))
            elif c_price <= self.strategy_config.low_stop_price or c_price >= self.strategy_config.high_stop_price:
                self.logger.warn("STOP_STRATEGY (current price:%s, low_stop_price:%s, High_stop_price:%s)", 
                                 c_price, self.strategy_config.low_stop_price, self.strategy_config.high_stop_price)
                return_code = 300 #stop the stragety
            else:
                self.logger.debug("do nothing cause high price: (target price: %s, current price: %s)", self.strategy_config.start_price, c_price)
        else:
            return_code = self.__prepare_open_steps(dif_no, c_price)
        
        self.logger.debug("self.strategy_config.open_steps: %s", self.strategy_config.open_steps)
        if (self.strategy_config.open_steps and self.strategy_config.open_steps[0].entrust_no is None):
            self.__buy_or_sell(self.strategy_config.open_steps[-1].bs_type, c_price,
                               sum([e.step_qty for e in self.strategy_config.open_steps]))
            self.logger.debug("show updated strategy: %s", str(self.strategy_config))
        
        return return_code
    
    
    def __check_entrust(self, c_price):
        return_code = 200
        _step = self.strategy_config.open_steps[-1]
        _entrust_no = _step.entrust_no
        self.logger.info("checking open entrust(%s)", _entrust_no)
        
        if _entrust_no is None:
            self.logger.info('handle the un-executed open steps: %s', self.strategy_config.open_steps)
            self.__buy_or_sell(_step.bs_type, _step.price,
                               sum([e.step_qty for e in self.strategy_config.open_steps]))
            return return_code
        
        e = self.account.get_entrust(_entrust_no)
        if e is None: # None means uncanceled/done
            self.__complete_entrust()            
            return_code = 100
        else:
            bs_type = _step.bs_type
            step_no = _step.step_no
            step_price = _step.step_price
            is_too_high = step_no>1 and bs_type==BsType.BUY and c_price-step_price>=2*self.strategy_config.step_margin
            is_too_low = step_no<self.strategy_config.total_num and bs_type==BsType.SELL and step_price-c_price>=2*self.strategy_config.step_margin
            if is_too_high or is_too_low:
                self.logger.warn("cancel open entrust(%s) because that price(%s, bs_type:%s) is not reasonable when the latest price is %s", 
                                 _entrust_no, step_price, bs_type, c_price)
                self.__cancel_entrust()
                return_code = 100
        return return_code
      
    def __prepare_open_steps(self, dif_no, c_price):
        return_code = 200
        last_step = self.strategy_config.completed_steps[-1]
        last_sprice = last_step.step_price
        last_no = last_step.step_no
        no_list = []
        
        if c_price<last_sprice and c_price<=self.strategy_config.start_price:
            c_type = BsType.BUY #buy
            c_no = dif_no+1
            if last_no>=self.strategy_config.total_num:
                self.logger.debug("below the low price")
                if c_price<=self.strategy_config.low_stop_price:# sell out all positions
                    self.logger.warn("STOP_BY_LOW_PRICE (current price:%s, low_stop_price:%s)", c_price, self.strategy_config.low_stop_price)
                    all_qty = sum(s.step_qty for s in self.strategy_config.completed_steps if s.bs_type==BsType.BUY) - sum(s.step_qty for s in self.strategy_config.completed_steps if s.bs_type==BsType.SELL)
                    self.logger.warn("SELL OUT ALL POSITIONS before stopping: all_qty=%s", all_qty)
                    if all_qty>0:
                        self.strategy_config.open_steps.append(StepPosition(step_no=100, step_price=self.strategy_config.low_stop_price, 
                                                                            step_qty=all_qty, price=c_price, bs_type=BsType.SELL, status=EntrustStatus.OPEN, 
                                                                            strategy=self.strategy_config))
                    return_code = 300
            elif c_no>=self.strategy_config.total_num:
                self.logger.debug("buy full positions from %s to the bottom step:%s instead of step:%s", last_no+1, self.strategy_config.total_num, c_no)
                no_list = list(range(last_no+1, self.strategy_config.total_num+1))
            else:
                no_list = list(range(last_no+1, c_no+1))
        elif c_price>last_sprice:
            c_type = BsType.SELL #sell
            
            if c_price>self.strategy_config.start_price:
                if last_no==0:
                    self.logger.debug("above the start price")
                    if c_price>=self.strategy_config.high_stop_price:
                        self.logger.warn("STOP_BY_HIGH_PRICE (current price:%s, high_stop_price:%s)", c_price, self.strategy_config.high_stop_price)
                        return_code = 300
                elif dif_no==0:
                    no_list = list(range(1,last_no))
                elif dif_no>0:
                    self.logger.debug("sell all positions, from step:%s to step:0", last_no-1)
                    no_list = list(range(0,last_no))
            else:
                c_no = dif_no+2
                no_list = list(range(c_no,last_no))
                no_list.reverse()
           
        self.logger.debug("no_list: %s", no_list) 
        for no in no_list:
            last_step =  self.strategy_config.open_steps[-1] if self.strategy_config.open_steps else self.strategy_config.completed_steps[-1]
            last_sprice = last_step.step_price
            last_type = last_step.bs_type
            last_qty = last_step.step_qty
            step_price = ahelper.format_money(last_sprice-self.strategy_config.step_margin 
                                             if c_type==BsType.BUY 
                                             else last_sprice+self.strategy_config.step_margin)
            if last_step.source is None:
                self.logger.info("link to the first step")
                qty = last_qty+self.strategy_config.unit_qty if last_type==c_type else self.strategy_config.unit_qty
                source = last_step
            elif last_step.step_no==0:
                if c_type==BsType.BUY:
                    self.logger.info("start a new loop!")
                    qty = self.strategy_config.unit_qty
                    source = None
                else:#TODO - throw exception
                    self.logger.error("UNEXPECTED - cannot sell stocks after last_step.step_no==0, current_price:%s \n strategy_config: %s", 
                                      c_price, self.strategy_config)
            elif last_qty==last_step.source.step_qty:
                self.logger.info("zero cleaning the last step chain! ")
                ss_step = last_step.source.source 
                if ss_step is None:
                    ss_step = last_step.source
                     
                if last_type==c_type:
                    qty = ss_step.step_qty+self.strategy_config.unit_qty
                    source = ss_step.source
                else:
                    qty = self.strategy_config.unit_qty
                    source = ss_step
            else:
                if last_type==c_type:
                    qty = last_qty+self.strategy_config.unit_qty
                    source = last_step.source
                else:
                    qty = self.strategy_config.unit_qty
                    source = last_step
            
            self.strategy_config.open_steps.append(StepPosition(source=source, step_no=no, step_price=step_price, step_qty=qty, 
                                                price=c_price, bs_type=c_type, status=EntrustStatus.OPEN, strategy=self.strategy_config))
        return return_code
            
    
    def __buy_or_sell(self, bs_type, price, qty):
        stock_code=self.strategy_config.stock_code
        self.logger.info('BUY_OR_SELL(bs_type=%s, stock_code=%s, price=%s, qty=%s)', bs_type, stock_code, price, qty)
        entrust_no = self.account.buy_or_sell(bs_type, stock_code, price, qty)
        self.logger.debug("set open entrust_no(%s)", entrust_no) 
        with db.atomic():             
            for s in self.strategy_config.open_steps:
                s.entrust_no = entrust_no
                s.qty = s.step_qty
                s.save() #TODO - improve the perfromance with batch insert 
     
    @db.atomic()
    def __complete_entrust(self):
        _entrust_no = self.strategy_config.open_steps[-1].entrust_no
        self.logger.info("Entrust(%s) completed! move open_steps to completed_steps!", _entrust_no)
        for p in self.strategy_config.open_steps:
            p.status = EntrustStatus.COMPLETED #completed
            p.updated_at = _datetime.datetime.now()
            p.save()
        self.strategy_config.completed_steps.extend(self.strategy_config.open_steps)
        self.strategy_config.open_steps.clear()
    
    @db.atomic()             
    def __cancel_entrust(self):
        _step = self.strategy_config.open_steps[-1]
        _entrust_no = _step.entrust_no
        self.logger.warn("CANCEL_ENTRUST - %s", _entrust_no)
        
        if _entrust_no is None:
            self.logger.info('do nothing to cancel the un-executed open steps: %s', self.strategy_config.open_steps)
            return
        
        self.logger.info('check entrust before canceling')
        e = self.account.get_entrust(_entrust_no)
        if e is None: # None means uncanceled/done
            self.logger.warn('entrust is completed before canceling')
            self.__complete_entrust()            
        else:
            actual_qty = e.actual_qty #deal with the partial completed case
            self.account.cancel_entrust(_entrust_no)
            for p in self.strategy_config.open_steps:
                if p.step_qty <= actual_qty:
                    actual_qty -= p.step_qty
                    p.status = EntrustStatus.COMPLETED
                    p.save()
                    self.strategy_config.completed_steps.append(p)
                elif 0 < actual_qty <= p.step_qty:
                    actual_qty -= 0
                    p.qty = actual_qty #part completed
                    p.status = EntrustStatus.COMPLETED
                    p.save()
                    self.strategy_config.completed_steps.append(p)
                else:
                    p.status = EntrustStatus.CANCELED # canceled
                    p.save()
            self.strategy_config.open_steps.clear()
