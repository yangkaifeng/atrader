'''
Created on 2016年4月16日

@author: andy.yang
'''
import os
from peewee import *
from atrader.util import ahelper 

connection_str = ahelper.file2dict(os.path.join(os.getcwd(), 'config', 'database.json'))
db = MySQLDatabase(**connection_str)

class BaseModel(Model):
    
    @classmethod
    def batch_insert(cls,rows):
        with db.atomic():
            Model.insert_many(rows).execute()
            
    class Meta:
        database = db 
        