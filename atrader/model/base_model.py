'''
Created on 2016年4月16日

@author: andy.yang
'''
import os
from peewee import *
from atrader.util import ahelper,atime

connection_str = ahelper.file2dict(ahelper.get_config_path('database.json'))
db = MySQLDatabase(**connection_str)

class BaseModel(Model):
    
#     @classmethod
#     def batch_insert(cls,rows):
#         with db.atomic():
#             Model.insert_many(rows).execute()
    created_at = DateTimeField(default=atime.now)
    updated_at = DateTimeField(default=atime.now)
         
    class Meta:
        database = db 
        