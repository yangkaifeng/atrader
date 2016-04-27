'''
Created on 2016年3月20日

@author: andy.yang
'''
import logging.config 
from robot import *

IS_TEST = True
logging.config.fileConfig("config\\logging.conf")

# create logger     
logger = logging.getLogger(__name__) 

def main():
    for robot in Robot.select_opens():
        robot.run() # @TODO multiple threads

if __name__ == '__main__':
    logger.info("%s start sbstrader %s", "#"*10, "#"*10)
    main()
    logger.info("%s stop sbstrader %s", "#"*10, "#"*10)