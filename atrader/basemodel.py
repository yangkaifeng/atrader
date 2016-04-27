'''
Created on 2016年4月16日

@author: andy.yang
'''
from peewee import *
import helper

connection_str = helper.file2dict('config\\database.json')
db = MySQLDatabase(**connection_str)

class BaseModel(Model):
    class Meta:
        database = db 
        