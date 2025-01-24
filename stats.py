from flask import Flask, Blueprint, jsonify
from imports import *

stats_api = Blueprint('stats_api', __name__)

# Collections from the database
USERS_COLLECTION = DB['users']
PARTS_COLLECTION = DB['parts']
SET_OVERVIEWS_COLLECTION = DB['set_overviews']
SET_CONTENTS_COLLECTION = DB['set_contents']
SET_SIMILARITIES_COLLECTION = DB['set_similarities']
SET_OFFERS_COLLECTION = DB['set_offers']
COLORS_COLLECTION = DB['colors']

def get_set_statistics():
    statistics = {}

    # Total number of sets
    total_sets = SET_OVERVIEWS_COLLECTION.count_documents({})
    # Number of sets with offers
    sets_with_offers = SET_OFFERS_COLLECTION.count_documents({"offers": {"$exists": True, "$ne": []}})

    # Set with the least number of offers
    set_with_less_offers = next(SET_OFFERS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "num_offers": {"$size": "$offers"}}},
        {"$sort": {"num_offers": 1}},
        {"$limit": 1}
    ]), None)

    # Set with the most number of offers
    set_with_most_offers = next(SET_OFFERS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "num_offers": {"$size": "$offers"}}},
        {"$sort": {"num_offers": -1}},
        {"$limit": 1}
    ]), None)

    # Most expensive set based on offers
    most_expensive_set = next(SET_OFFERS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "max_price": {"$max": {"$map": {"input": "$offers", "as": "offer", "in": "$$offer.price"}}}}}, 
        {"$sort": {"max_price": -1}}, 
        {"$limit": 1}
    ]), None)

    # Least expensive set based on offers
    less_expensive_set = next(SET_OFFERS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "max_price": {"$max": {"$map": {"input": "$offers", "as": "offer", "in": "$$offer.price"}}}}}, 
        {"$sort": {"max_price": 1}}, 
        {"$limit": 1}
    ]), None)

    # Average number of parts per set
    average_parts_result = SET_OVERVIEWS_COLLECTION.aggregate([{
        '$group': {'_id': None, 'average_parts_per_set': {'$avg': '$num_parts'}}
    }])
    average_parts_per_set = round(next(average_parts_result, {}).get('average_parts_per_set', 0), 2)

    # Set with the most parts
    sets_with_the_most_parts = next(SET_OVERVIEWS_COLLECTION.find({}, {'_id': 1, 'name': 1, 'num_parts': 1}).sort('num_parts', -1).limit(1), None)
    # Set with the least parts
    sets_with_the_less_parts = next(SET_OVERVIEWS_COLLECTION.find({}, {'_id': 1, 'name': 1, 'num_parts': 1}).sort('num_parts', 1).limit(1), None)

    statistics['sets'] = {
        "total_sets": total_sets,
        "sets_with_offers": sets_with_offers,
        "average_parts_per_set": average_parts_per_set,
        "sets_with_the_most_parts": sets_with_the_most_parts,
        "sets_with_the_less_parts": sets_with_the_less_parts,
        "set_with_less_offers": set_with_less_offers,
        "set_with_most_offers": set_with_most_offers,
        "most_expensive_set": most_expensive_set,
        "less_expensive_set": less_expensive_set
    }

    return statistics

def get_part_statistics():
    statistics = {}

    # Total number of parts
    total_parts = PARTS_COLLECTION.count_documents({})

    # Distribution of colors among parts
    color_counts = PARTS_COLLECTION.aggregate([
        {"$project": {"colors": {"$objectToArray": "$colors"}}},
        {"$unwind": "$colors"},
        {"$group": {"_id": "$colors.k", "count": {"$sum": {"$size": "$colors.v"}}}}
    ])
    colors_distribution = {doc["_id"]: doc["count"] for doc in color_counts}

    # Part with the most offers
    part_with_most_offers = next(PARTS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "num_offers": {"$sum": [{"$size": {"$ifNull": [{"$objectToArray": "$colors"}, []]}}]}}},
        {"$sort": {"num_offers": -1}},
        {"$limit": 1}
    ]), None)

    # Part with the least offers
    part_with_less_offers = next(PARTS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "num_offers": {"$sum": [{"$size": {"$ifNull": [{"$objectToArray": "$colors"}, []]}}]}}},
        {"$sort": {"num_offers": 1}},
        {"$limit": 1}
    ]), None)

    # Cheapest part based on offers
    cheapest_part = next(PARTS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "min_price": {"$min": {"$map": {"input": {"$objectToArray": "$colors"}, "as": "color", "in": {"$min": {"$map": {"input": "$$color.v", "as": "offer", "in": "$$offer.Price"}}}}}}}},
        {"$sort": {"min_price": 1}},
        {"$limit": 1}
    ]), None)

    # Most expensive part based on offers
    most_expensive_part = next(PARTS_COLLECTION.aggregate([
        {"$project": {"_id": 1, "max_price": {"$max": {"$map": {"input": {"$objectToArray": "$colors"}, "as": "color", "in": {"$max": {"$map": {"input": "$$color.v", "as": "offer", "in": "$$offer.Price"}}}}}}}},
        {"$sort": {"max_price": -1}},
        {"$limit": 1}
    ]), None)

    statistics['parts'] = {
        "total_parts": total_parts,
        "colors_distribution": colors_distribution,
        "part_with_less_offers": part_with_less_offers,
        "part_with_most_offers": part_with_most_offers,
        "cheapest_part": cheapest_part,
        "most_expensive_part": most_expensive_part
    }

    return statistics

def get_user_statistics():
    statistics = {}

    # Total number of users
    total_users = USERS_COLLECTION.count_documents({})
    # Number of users with sets in their inventory
    users_with_sets = USERS_COLLECTION.count_documents({"inventory.sets": {"$exists": True, "$ne": []}})
    # Number of users with parts in their inventory
    users_with_parts = USERS_COLLECTION.count_documents({"inventory.parts": {"$exists": True, "$ne": []}})

    # User with the most parts
    user_with_most_parts = next(USERS_COLLECTION.aggregate([
        {"$project": {"parts": {"$objectToArray": "$inventory.parts"}}},
        {"$unwind": "$parts"},
        {"$project": {"part_values": {"$objectToArray": "$parts.v"}}},
        {"$unwind": "$part_values"},
        {"$group": {"_id": "$_id", "num_parts": {"$sum": {"$toInt": "$part_values.v"}}}},
        {"$sort": {"num_parts": -1}},
        {"$limit": 1}
    ]), None)

    # User with the least parts
    user_with_less_parts = next(USERS_COLLECTION.aggregate([
        {"$project": {"parts": {"$objectToArray": "$inventory.parts"}}},
        {"$unwind": "$parts"},
        {"$project": {"part_values": {"$objectToArray": "$parts.v"}}},
        {"$unwind": "$part_values"},
        {"$group": {"_id": "$_id", "num_parts": {"$sum": {"$toInt": "$part_values.v"}}}},
        {"$sort": {"num_parts": 1}},
        {"$limit": 1}
    ]), None)

    # User with the most sets
    user_with_most_sets = next(USERS_COLLECTION.aggregate([
        {"$project": {"sets": {"$objectToArray": "$inventory.sets"}}},
        {"$unwind": "$sets"},
        {"$project": {"set_id": "$sets.k"}},
        {"$group": {"_id": "$_id", "unique_sets": {"$addToSet": "$set_id"}}},
        {"$project": {"_id": 1, "num_sets": {"$size": "$unique_sets"}}},
        {"$sort": {"num_sets": -1}},
        {"$limit": 1}
    ]), None)

    # User with the least sets
    user_with_less_sets = next(USERS_COLLECTION.aggregate([
        {"$project": {"sets": {"$objectToArray": "$inventory.sets"}}},
        {"$unwind": "$sets"},
        {"$project": {"set_id": "$sets.k"}},
        {"$group": {"_id": "$_id", "unique_sets": {"$addToSet": "$set_id"}}},
        {"$project": {"_id": 1, "num_sets": {"$size": "$unique_sets"}}},
        {"$sort": {"num_sets": 1}},
        {"$limit": 1}
    ]), None)

    # Most frequent part in users' inventories
    most_frequent_part = next(USERS_COLLECTION.aggregate([
        {"$project": {"parts": {"$objectToArray": "$inventory.parts"}}},
        {"$unwind": "$parts"},
        {"$group": {"_id": "$parts.k", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]), None)

    # Least frequent part in users' inventories
    less_frequent_part = next(USERS_COLLECTION.aggregate([
        {"$project": {"parts": {"$objectToArray": "$inventory.parts"}}},
        {"$unwind": "$parts"},
        {"$group": {"_id": "$parts.k", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}},
        {"$limit": 1}
    ]), None)

    # Most frequent set in users' inventories
    most_frequent_set = next(USERS_COLLECTION.aggregate([
        {"$project": {"sets": {"$objectToArray": "$inventory.sets"}}},
        {"$unwind": "$sets"},
        {"$group": {"_id": "$sets.k", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]), None)

    # Least frequent set in users' inventories
    less_frequent_set = next(USERS_COLLECTION.aggregate([
        {"$project": {"sets": {"$objectToArray": "$inventory.sets"}}},
        {"$unwind": "$sets"},
        {"$group": {"_id": "$sets.k", "count": {"$sum": 1}}},
        {"$sort": {"count": 1}},
        {"$limit": 1}
    ]), None)

    statistics['users'] = {
        "total_users": total_users,
        "users_with_sets": users_with_sets,
        "users_with_parts": users_with_parts,
        "user_with_most_parts": user_with_most_parts,
        "user_with_less_parts": user_with_less_parts,
        "user_with_most_sets": user_with_most_sets,
        "user_with_less_sets": user_with_less_sets,
        "most_frequent_part": most_frequent_part,
        "less_frequent_part": less_frequent_part,
        "most_frequent_set": most_frequent_set,
        "less_frequent_set": less_frequent_set
    }

    return statistics

@stats_api.route('', methods=['GET'])
def database_statistics():
    statistics = {}
    statistics.update(get_set_statistics())
    statistics.update(get_part_statistics())
    statistics.update(get_user_statistics())
    return jsonify(statistics)
