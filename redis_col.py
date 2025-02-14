import redis
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

# Połączenie z Redis
r = redis.StrictRedis(host='10.1.1.45', port=6379, db=0)
# Połączenie z MongoDB
CLIENT = MongoClient(os.getenv('MONGO_URI'))
DB = CLIENT['bricks']
PARTS_COLLECTION = DB['parts']

#  mapy ID -> name colors from Redis
color_map = {}

cursor = 0
while True:
    cursor, keys = r.scan(cursor, match="colors:*:name")
    for key in keys:
        color_name = r.get(key)
        if color_name:
            color_id = key.decode('utf-8').split(':')[1]  
            color_map[color_name.decode('utf-8').lower()] = color_id  # Map name to ID
    if cursor == 0:
        break

# Mapping functtion
def map_colors_to_id(parts_data, color_map):
    if "colors" not in parts_data:
        return parts_data 

    updated_colors = {}  

    if isinstance(parts_data["colors"], dict):  
        for color_name, items in parts_data["colors"].items():
            color_id = color_map.get(color_name.lower())  
            if color_id:
                updated_colors[color_id] = items

    elif isinstance(parts_data["colors"], list):  
        new_colors_list = []
        for color_data in parts_data["colors"]:
            if isinstance(color_data, dict):  
                color_name = color_data.get("color_name")
            elif isinstance(color_data, str):  
                color_name = color_data
                color_data = {}  # Dictionery from redis
            else:
                continue

            if color_name:
                color_id = color_map.get(color_name.lower())  
                if color_id:
                    color_data["color_id"] = color_id
                    new_colors_list.append(color_data)

        updated_colors = new_colors_list  #Write only if exist

    # if no color dont write
    if updated_colors:
        parts_data["colors"] = updated_colors
        
    return parts_data

def update_all_parts_in_mongo(color_map):
    all_parts = PARTS_COLLECTION.find()  

    for part_data in all_parts:
        updated_part_data = map_colors_to_id(part_data, color_map)

        if "colors" in updated_part_data and updated_part_data["colors"]: 
            result = PARTS_COLLECTION.update_one(
                {"_id": updated_part_data["_id"]},
                {"$set": {"colors": updated_part_data["colors"]}}
            )


update_all_parts_in_mongo(color_map)
