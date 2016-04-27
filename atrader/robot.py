'''
Created on 2016年3月20日

@author: andy.yang
'''
from peewee import *
import logging.config 
from time import sleep
import time
from account import *
from main import *
from basemodel import *

QUATION_INTERVAL = 1 #if IS_TEST else 5 #seconds

# logging.config.fileConfig("logging.conf")
# create logger     
logger = logging.getLogger(__name__)

class Strategy(BaseModel):
    '''
    classdocs
    '''
    account_code = CharField()
    stock_code = CharField()
    start_price = DoubleField()
    step_ratio = DoubleField()
    total_num = IntegerField()
    unit_qty = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.now)
    high_stop_ratio = DoubleField()
    low_stop_ratio = DoubleField()
    
    @property
    def step_margin(self):
        if not hasattr(self, '_step_margin'):
            self._step_margin = helper.format_money(self.start_price*self.step_ratio)
        return self._step_margin
    
    @property
    def high_stop_price(self):
        if not hasattr(self, '_high_stop_price'):
            self._high_stop_price = helper.format_money((self.start_price+self.step_margin)*(1+self.high_stop_ratio))
        return self._high_stop_price
    
    @property
    def low_stop_price(self):
        if not hasattr(self, '_low_stop_price'):
            self._low_stop_price = helper.format_money(self.start_price*(1-self.step_ratio*(self.total_num-1))*(1-self.low_stop_ratio))
        return self._low_stop_price
    
    @property
    def completed_steps(self):
        if not hasattr(self, '_completed_steps'):
            self._completed_steps = [p for p in self.steps if p.status==2]
        return self._completed_steps
    
    @property
    def open_steps(self):
        if not hasattr(self, '_open_steps'):
            self._open_steps = [p for p in self.steps if p.status==1]
        return self._open_steps
    
    @property
    def open_entrust_no(self):
        if not hasattr(self, '_open_entrust_no'):
            self._open_entrust_no = self.open_steps[0].entrust_no if self.open_steps else None
        return self._open_entrust_no
    
    @open_entrust_no.setter
    def open_entrust_no(self, no):
        self._open_entrust_no = no

    def __repr__(self):
        return "strategy(stock=%s, unit_qty=%s, total_num=%s,\
        start_price=%s, step_ratio=%s,step_margin=%s, open_entrust_no=%s,\
        \nsteps=%s,\nopen_steps=%s" % (self.stock_code,self.unit_qty,self.total_num,self.start_price,self.step_ratio,
                                      self.step_margin,self.open_entrust_no,self.completed_steps,self.open_steps)
    
    def __check_entrust(self, c_price):
        logger.info("check entrust list")
        return_code = 400
        acc = Account(self.account_code)
        e = acc.get_entrust(self.open_entrust_no)
        if e is None: # None means uncanceled/done
            logger.info("Entrust completed! move open_steps to steps!")
            for p in self.open_steps:
                p.status = 2 #completed
                p.updated_at = datetime.datetime.now()
                p.save()
            self.completed_steps.extend(self.open_steps)
            self.open_entrust_no = None
            self.open_steps.clear()
            return_code = 100
        elif self.completed_steps:
            bs_type = self.open_steps[-1].bs_type
            step_price = self.open_steps[-1].step_price
            if (bs_type==1 and c_price-step_price>=2*self.step_margin) or (bs_type==2 and step_price-c_price>=2*self.step_margin):
                logger.warn("Cancel entrust automatically! price is changed too much!")
                acc.cancel_entrust(self.open_entrust_no)
                for p in self.open_steps:
                    p.status = 3 # canceled
                    p.save()
                self.open_entrust_no = None
                self.open_steps.clear()
                return_code = 100
        return return_code
      
    def __prepare_open_steps(self, dif_no, c_price):
        return_code = 400
        last_step = self.completed_steps[-1]
        last_sprice = last_step.step_price
        last_no = last_step.step_no
        no_list = []
        
        if c_price<last_sprice and c_price<=self.start_price:
            c_type = 1 #buy
            c_no = dif_no+1
            if last_no>=self.total_num:
                logger.debug("below the low price")
                if c_price<=self.low_stop_price:# sell out all positions
                    logger.warn("TOO LOW PRICE, already below the low stop price(%s), should stop the robot!", self.low_stop_price)
                    return_code = 300
                    all_qty = sum(s.step_qty for s in self.completed_steps if s.bs_type==1) - sum(s.step_qty for s in self.completed_steps if s.bs_type==2)
                    acc = Account(self.account_code)
                    acc.buy_or_sell(2,self.stock_code, c_price, all_qty)#TODO - save this operation
                    logger.warn("SELL OUT ALL POSITIONS before stopping: all_qty=%s", all_qty)
            elif c_no>=self.total_num:
                logger.debug("buy full positions from %s to the bottom step:%s instead of step:%s", last_no+1, self.total_num, c_no)
                no_list = list(range(last_no+1, self.total_num+1))
            else:
                no_list = list(range(last_no+1, c_no+1))
        elif c_price>last_sprice:
            c_type = 2 #sell
            
            if c_price>self.start_price:
                if last_no==0:
                    logger.debug("above the start price")
                    if c_price>=self.high_stop_price:
                        logger.warn("TOO HIGH PRICE, already above the high stop price(%s), should stop the robot!", self.high_stop_price)
                        return_code = 300
                elif dif_no==0:
                    no_list = list(range(1,last_no))
                elif dif_no>0:
                    logger.debug("sell all positions, from step:%s to step:0", last_no-1)
                    no_list = list(range(0,last_no))
            else:
                c_no = dif_no+2
                no_list = list(range(c_no,last_no))
                no_list.reverse()
           
        logger.debug("no_list: %s", no_list) 
        for no in no_list:
            last_step =  self.open_steps[-1] if self.open_steps else self.completed_steps[-1]
            last_sprice = last_step.step_price
            last_type = last_step.bs_type
            last_qty = last_step.step_qty
            step_price = helper.format_money(last_sprice-self.step_margin 
                                             if c_type==1 
                                             else last_sprice+self.step_margin)
            if last_step.source is None:
                logger.info("link to the first step")
                qty = last_qty+self.unit_qty if last_type==c_type else self.unit_qty
                source = last_step
            elif last_step.step_no==0:
                if c_type==1:
                    logger.info("start a new loop!")
                    qty = self.unit_qty
                    source = None
                else:#TODO - throw exception
                    logger.error("UNEXPECTED - can't sell stocks after last_step.step_no==0")
            elif last_qty==last_step.source.step_qty:
                logger.info("zero cleaning the last step chain! ")
                ss_step = last_step.source.source 
                if ss_step is None:
                    ss_step = last_step.source
                     
                if last_type==c_type:
                    qty = ss_step.step_qty+self.unit_qty
                    source = ss_step.source
                else:
                    qty = self.unit_qty
                    source = ss_step
            else:
                if last_type==c_type:
                    qty = last_qty+self.unit_qty
                    source = last_step.source
                else:
                    qty = self.unit_qty
                    source = last_step
            
            self.open_steps.append(StepPosition(source=source, step_no=no, step_price=step_price, step_qty=qty, 
                                                price=c_price, bs_type=c_type, status=1, strategy=self))
        return return_code
            
    def think(self):
        '''
        check entrust orders first
        get latest stock price
        think actions 
        return {"code":100/200/300,"bs_type":1 or 2, "price":price, "qty":qty}
        '''
        logger.debug("think about what to do")
        acc = Account(self.account_code)
        price_info = acc.get_stock(self.stock_code)
        c_price = price_info["now"]
        dif_no = int(abs(self.start_price-c_price)//self.step_margin)
        logger.debug("current price: %s, dif_no:%s", c_price, dif_no)
        return_code = 200
        
        if self.open_entrust_no:
            logger.debug("already have an entrust")
            return_code = self.__check_entrust(c_price)
        elif self.completed_steps==[]:
            if c_price<=self.start_price: #buy first position 
                logger.info("buy first batch of positions")
                for no in range(1,dif_no+2):
                    start_pos = self.open_steps[0] if self.open_steps else None
                    s_price = helper.format_money(self.start_price-(no-1)*self.step_margin)
                    self.open_steps.append(StepPosition(source=start_pos, step_no=no, step_price=s_price, step_qty=no*self.unit_qty, 
                                                        price=c_price, bs_type=1, status=1, strategy=self))
            else:
                logger.debug("do nothing cause high price: (target price: %s, current price: %s)", self.start_price, c_price)
        else:
            return_code = self.__prepare_open_steps(dif_no, c_price)
        
        logger.debug("self.open_steps: %s", self.open_steps)
        if (self.open_steps and self.open_entrust_no is None):
            decision = {"code":200,
                        "bs_type":self.open_steps[-1].bs_type,
                        "stock_code":self.stock_code,
                        "price":c_price, 
                        "qty":sum([e.step_qty for e in self.open_steps])}
        else: 
            decision = {"code": return_code}
        return decision # None means nothing to do
    
    def set_entrust_no(self, entrust_no):
        logger.info("binding a new entrust_no(%s) with the strategy", entrust_no)
        self.open_entrust_no = entrust_no
        for s in self.open_steps:
            s.entrust_no = entrust_no
            s.save()

class StepPosition(BaseModel):
    '''
    classdocs
    '''
    strategy = ForeignKeyField(Strategy, related_name='steps')
    source = ForeignKeyField('self', related_name='children', null=True)
    step_no = IntegerField()
    step_price = DoubleField()
    step_qty = IntegerField()
    price = DoubleField()
    bs_type = IntegerField()
    entrust_no = CharField()
    status = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    
#     class Meta:
#         order_by = ('id') 
        
    def __repr__(self):
        if self.source is None:
            return "\nStepPosition{id:%s,source:None,step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,entrust_no:%s,status:%s,strategy_id:%s,created_at:%s}"\
                 % (self.id, self.step_no,self.step_price,self.step_qty,self.price,self.bs_type,self.entrust_no,self.status,self.strategy_id,self.created_at)
        else:
            return "\nStepPosition{id:%s,source:{bs_type=%s,price=%s,step_qty=%s},step_no:%s,step_price:%s,step_qty:%s,price:%s,bs_type:%s,entrust_no:%s,status:%s,strategy_id:%s,created_at:%s}"\
                 % (self.id, self.source.bs_type,self.source.price,self.source.step_qty,self.step_no,self.step_price,self.step_qty,
                    self.price,self.bs_type,self.entrust_no,self.status,self.strategy_id,self.created_at)
    
class Robot(BaseModel):
    '''
    classdocs
    '''
    strategy = ForeignKeyField(Strategy, related_name='strategy_robot')
    account_code = CharField()
    status = IntegerField(default=1) # 1-new, 2-open, 3-close
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    @classmethod
    def select_opens(cls):
        return cls.select().where(cls.status==2)
    
    def run(self): 
        oplog = RobotOplog.create(robot=self)
        while True:
            now_hour = time.localtime().tm_hour
            now_min = time.localtime().tm_min
            if IS_TEST or (now_hour==9 and now_min>=30) or (now_hour in (10,13,14)) or (now_hour==11 and now_min<=30):
                logger.debug("market is open")
                acc = Account(self.account_code)
                decision = self.strategy.think()
                logger.debug("decision: %s", decision)
                if decision['code']==100: #continue
                    continue
                elif decision['code']==300: #close the robot
                    self.status=3
                    self.updated_at = datetime.datetime.now()
                    self.save()
                    break
                else:
                    if decision['code']==200:
                        logger.info("we have a decision to do: %s", decision)
                        entrust_no = acc.buy_or_sell(decision["bs_type"], decision["stock_code"], decision["price"], decision["qty"])
                        self.strategy.set_entrust_no(entrust_no)
                        logger.debug("show updated strategy: %s", str(self.strategy))
                    logger.debug("sleep for %s seconds", QUATION_INTERVAL)  
                    sleep(QUATION_INTERVAL)
            else:
                logger.debug("sleep for 10 minutes")  
                sleep(600) # 10 minutes
                
        oplog.stopped_at = datetime.datetime.now()
        oplog.save()        

class RobotOplog(BaseModel):
    robot = ForeignKeyField(Robot, related_name='oplogs')
    started_at = DateTimeField(default=datetime.datetime.now)
    stopped_at = DateTimeField(null=True)
    
def create_tabels():
    db.connect()
    logger.debug("create all tables in database!")
    db.create_tables([Strategy, StepPosition, Robot, RobotOplog])
    db.close()
    
def setup_testdata():
    s = Strategy.create(account_code='666623491885', stock_code='002024', unit_qty=100, total_num=10, 
                        start_price=10.0, step_ratio=0.01, low_stop_ratio=0.5, high_stop_ratio=0.5)
    r = Robot.create(account_code='666623491885', strategy=s, status=2)
    logger.debug("create test_data")
    return r

def setup_proddata():
    s = Strategy.create(account_code='666623491885', stock_code='600602', unit_qty=1000, total_num=5, start_price=11.4, step_ratio=0.01)
    r = Robot.create(account_code='666623491885', strategy=s)
    logger.debug("create test_data")
    return r
        
if __name__ == "__main__":
#     create_tabels()
#     setup_proddata()
    setup_testdata()
#     db.create_table(RobotOplog)