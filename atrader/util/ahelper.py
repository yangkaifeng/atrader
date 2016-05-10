'''
Created on 2016年4月4日

@author: andy.yang
'''
import json 

def format_money(p):
    return round(p,2)

def format_ratio(r):
    return round(r,4)

def file2dict(path):
    with open(path) as f:
        return json.load(f)
    
    
if __name__ == '__main__':
    print(format_money(10.123123))
    print(format_ratio(0.123123))