from flask import Flask, request, jsonify
from pymongo.errors import DuplicateKeyError
from pymongo import MongoClient
import redis
from dotenv import load_dotenv
import os
load_dotenv()

CLIENT = MongoClient(os.getenv('MONGO_URI'))
REDIS = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
DB = CLIENT['bricks']