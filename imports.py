from flask import Flask, Blueprint, request, jsonify
from pymongo.errors import DuplicateKeyError
from pymongo import MongoClient
import redis
from dotenv import load_dotenv
import os
import time
load_dotenv()

CLIENT = MongoClient(os.getenv('MONGO_URI'))
REDIS = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
DB = CLIENT['bricks']

def timeit(func): 
    '''Decorator that reports the execution time.'''
  
    def wrap(*args, **kwargs): 
        start = time.perf_counter() 
        result = func(*args, **kwargs) 
        end = time.perf_counter() 
          
        print(func.__name__, end-start) 
        return result 
    return wrap 

def redis_cache(module, expire=60): 
    '''Decorator that saves query result in redis.
    
    Args:
        module (str): The module name.
        expire (int): The expiration time in minutes.
    '''
    def decorator(func):
        def wrap(*args, **kwargs): 
            query = f"requests:{module}:{func.__name__}:"
            for i, item in enumerate(kwargs):
                if i != 0:
                    query += '-'
                query += f"{kwargs[item]}"

            if a:=REDIS.get(query):
                return jsonify(a)
        
            result = func(*args, **kwargs)
            if result.status_code != 200:
                print('Not caching error response...')
                return result
            print('Inserting into cache...')
            REDIS.set(query, str(result.json), ex=expire*60)
            return result
        wrap.__name__ = func.__name__
        return wrap
    return decorator
