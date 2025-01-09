from imports import *

SETS_COLLECTION = DB['sets']
PARTS_COLLECTION = DB['parts']

def all_set_ids():
    return set(str(_set['_id']) for _set in SETS_COLLECTION.find({}))

def all_part_ids():
    return set(str(part['_id']) for part in PARTS_COLLECTION.find({}))


def store_set_stats(set_id, visit_count=0, brick_value=0.0, profit_value=0.0):
    """
    Store stats for a set in Redis.
    
    Args:
        set_id (str): Unique identifier of the set.
        visit_count (int): Visit count for the set.
        brick_value (float): Value of the bricks in the set.
        profit_value (float): Profit value of the set.
    """
    set_key = f"set:{set_id}"
    stats = {
        "visit_count": visit_count,
        # "brick_value": brick_value,
        # "profit_value": profit_value
    }
    
    # Store the stats in a Redis hash
    REDIS.hmset(set_key, stats)
    
    # Track the set key in a global set of all sets
    REDIS.sadd("all_sets", set_key)

def put_sets():
    for _set in all_set_ids():
        store_set_stats(_set)

def get_set_stats(set_id):
    """
    Get stats for a set from Redis.
    
    Args:
        set_id (str): Unique identifier of the set.
        
    Returns:
        dict: Stats for the set.
    """
    set_key = f"set:{set_id}"
    stats = REDIS.hgetall(set_key)
    return stats
    
def get_all_set_stats():
    """
    Get stats for all sets from Redis.
    
    Returns:
        list: Stats for all sets.
    """
    all_sets = REDIS.smembers("all_sets")
    stats = [{set_key: REDIS.hgetall(set_key)} for set_key in all_sets]
    return stats

print(get_all_set_stats()[:10])