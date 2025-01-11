from flask import Flask
from flask import Blueprint
from imports import *

stats_api = Blueprint('stats_api', __name__)
USERS_COLLECTION = DB['users']
PARTS_COLLECTION = DB['parts']
SET_OVERVIEWS_COLLECTION = DB['set_overviews']
SET_CONTENTS_COLLECTION = DB['set_contents']
SET_SIMILARITIES_COLLECTION = DB['set_similarities']
SET_OFFERS_COLLECTION = DB['set_offers']
COLORS_COLLECTION = DB['colors']

@stats_api.route('', methods=['GET'])
def database_statistics():
    statistics = {}
    
    #SETS
    total_sets = SET_OVERVIEWS_COLLECTION.count_documents({})
    sets_with_offers = SET_OFFERS_COLLECTION.count_documents({"offers": {"$exists": True, "$ne": []}})
    set_with_less_offers = SET_OFFERS_COLLECTION.aggregate([
    {
        "$project": {
            "_id": 1,
            "num_offers": {"$size": "$offers"}
        }
    },
    {"$sort": {"num_offers": 1}},  
    {"$limit": 1}  ])
    set_with_less_offers = next(set_with_less_offers, None)

    set_with_most_offers = SET_OFFERS_COLLECTION.aggregate([
    {
        "$project": {
            "_id": 1,
            "num_offers": {"$size": "$offers"}
        }
    },
    {"$sort": {"num_offers": -1}},  
    {"$limit": 1}  ])
    set_with_most_offers = next(set_with_most_offers, None)
    
    most_expensive_set = SET_OFFERS_COLLECTION.aggregate([
    {"$project": {"_id": 1,"max_price": {
                "$max": {
                    "$map": {
                        "input": "$offers",  
                        "as": "offer",
                        "in": "$$offer.price"   }}}}},
    {"$sort": {"max_price": -1}}, 
    {"$limit": 1}  ])
    most_expensive_set = next(most_expensive_set, None)

    less_expensive_set = SET_OFFERS_COLLECTION.aggregate([
    {"$project": {"_id": 1,"max_price": {
                "$max": {
                    "$map": {
                        "input": "$offers",  
                        "as": "offer",
                        "in": "$$offer.price"  }}}}},
    {"$sort": {"max_price": 1}}, 
    {"$limit": 1}  ])
    less_expensive_set = next(less_expensive_set, None)


    average_parts_result = SET_OVERVIEWS_COLLECTION.aggregate([{
            '$group': {
                '_id': None,
                'average_parts_per_set': {'$avg': '$num_parts'}
            }
        }
    ])
    average_parts_per_set = next(average_parts_result, {}).get('average_parts_per_set', 0)
    average_parts_per_set = round(average_parts_per_set, 2)

    #set with the most parts
    sets_with_the_most_parts = SET_OVERVIEWS_COLLECTION.find({}, {'_id': 1, 'name': 1, 'num_parts': 1}) \
    .sort('num_parts', -1) \
    .limit(1)
    sets_with_the_most_parts = next(sets_with_the_most_parts, None)

    #set with the less parts
    sets_with_the_less_parts = SET_OVERVIEWS_COLLECTION.find({}, {'_id': 1, 'name': 1, 'num_parts': 1}) \
    .sort('num_parts', 1) \
    .limit(1)
    sets_with_the_less_parts = next(sets_with_the_less_parts, None)


    #PARTS
    total_parts = PARTS_COLLECTION.count_documents({})
    color_counts = PARTS_COLLECTION.aggregate([
    {"$project": {
        "colors": {"$objectToArray": "$colors"}
    }},

    {"$unwind": "$colors"},
    {"$group": {
        "_id": "$colors.k",
        "count": {"$sum": {"$size": "$colors.v"}} }}])
    colors_distribution = {doc["_id"]: doc["count"] for doc in color_counts}

    part_with_most_offers = PARTS_COLLECTION.aggregate([
    {
        "$project": {
            "_id": 1,
            "num_offers": {
                "$sum": [
                    {"$size": {"$ifNull": [{"$objectToArray": "$colors"}, []]}}
                ] 
            }
        }
    },
    {"$sort": {"num_offers": -1}},  
    {"$limit": 1}  
    ])
    part_with_most_offers = next(part_with_most_offers, None)

    part_with_less_offers = PARTS_COLLECTION.aggregate([
    {
        "$project": {
            "_id": 1,
            "num_offers": {
                "$sum": [
                    {"$size": {"$ifNull": [{"$objectToArray": "$colors"}, []]}}
                ] 
            }
        }
    },
    {"$sort": {"num_offers": 1}},  
    {"$limit": 1}  
    ])
    part_with_less_offers = next(part_with_less_offers, None)

    #cheapest_part
    cheapest_part = PARTS_COLLECTION.aggregate([\
    {
        "$project": {"_id": 1,"min_price": { "$min": { "$map": {"input": {"$objectToArray": "$colors"},"as": "color", "in": {
                            "$min": {
                                "$map": {
                                    "input": "$$color.v",  # Tablica ofert
                                    "as": "offer",
                                    "in": "$$offer.Price"  # Ceny ofert
    }}}}}}}},
    {"$sort": {"min_price": 1}},  # Sortujemy po najmniejszej cenie rosnąco
    {"$limit": 1}  # Zwracamy tylko część z najniższą ceną
    ])

    cheapest_part = next(cheapest_part, None)

    #most_expensive_part
    most_expensive_part = PARTS_COLLECTION.aggregate([
    # Rozwijamy każdą ofertę z kolorów, aby uzyskać cenę
    {
        "$project": {
            "_id": 1, "max_price": {"$max": { "$map": { "input": {"$objectToArray": "$colors"},"as": "color","in": {
                            "$max": {
                                "$map": {
                                    "input": "$$color.v",
                                    "as": "offer",
                                    "in": "$$offer.Price"  
    }}}}}}}},
    {"$sort": {"max_price": -1}},  # Sortujemy po najwyższej cenie malejąco
    {"$limit": 1}  # Zwracamy tylko część z najwyższą ceną
    ])

    most_expensive_part = next(most_expensive_part, None)


    #USERS
    total_users = USERS_COLLECTION.count_documents({})
    users_with_sets = USERS_COLLECTION.count_documents({"inventory.sets": {"$exists": True, "$ne": []}})
    users_with_parts = USERS_COLLECTION.count_documents({"inventory.parts": {"$exists": True, "$ne": []}})
    user_with_most_parts = USERS_COLLECTION.aggregate([
    {"$project": {
        "parts": {"$objectToArray": "$inventory.parts"}
    }},
    {"$unwind": "$parts"}, 
    {
        "$project": {
            "part_values": {"$objectToArray": "$parts.v"}
        }
    },
    {"$unwind": "$part_values"},  
    {
        "$group": {
            "_id": "$_id",  # Group by user ID
            "num_parts": {"$sum": {"$toInt": "$part_values.v"}}  
        }
    },
    {"$sort": {"num_parts": -1}}, 
    {"$limit": 1}  
    ])
    user_with_most_parts = next(user_with_most_parts, None)

    user_with_less_parts = USERS_COLLECTION.aggregate([
    {"$project": {
        "parts": {"$objectToArray": "$inventory.parts"}
    }},
    {"$unwind": "$parts"}, 
    {
        "$project": {
            "part_values": {"$objectToArray": "$parts.v"}
        }
    },
    {"$unwind": "$part_values"},  
    {
        "$group": {
            "_id": "$_id", 
            "num_parts": {"$sum": {"$toInt": "$part_values.v"}}  
        }
    },
    {"$sort": {"num_parts": 1}}, 
    {"$limit": 1}  
    ])
    user_with_less_parts = next(user_with_less_parts, None)
    

    #USER-SETS
    user_with_most_sets = USERS_COLLECTION.aggregate([
    # Convert 'inventory.sets' into an array of key-value pairs (set ID and its count)
    {"$project": {
        "sets": {"$objectToArray": "$inventory.sets"}  # Convert 'sets' into an array of set IDs
    }},
    {"$unwind": "$sets"},  # Unwind the array to process each set
    {
        "$project": {
            "set_id": "$sets.k"  # Only select the set ID (key)
        }
    },
    {
        "$group": {
            "_id": "$_id",  # Group by user ID
            "unique_sets": {"$addToSet": "$set_id"}  # Add unique set IDs to a set
        }
    },
    {
        "$project": {
            "_id": 1,  # Retain the user ID
            "num_sets": {"$size": "$unique_sets"}  # Count the number of unique sets
        }
    },
    {"$sort": {"num_sets": -1}},  # Sort by number of unique sets in descending order
    {"$limit": 1}  # Only keep the top user
    ])

    user_with_most_sets = next(user_with_most_sets, None)

    user_with_less_sets = USERS_COLLECTION.aggregate([
    {"$project": {
        "sets": {"$objectToArray": "$inventory.sets"} 
    }},
    {"$unwind": "$sets"}, 
    {
        "$project": {
            "set_id": "$sets.k" 
        }
    },
    {
        "$group": {
            "_id": "$_id",  
            "unique_sets": {"$addToSet": "$set_id"}  
        }
    },
    {
        "$project": {
            "_id": 1, 
            "num_sets": {"$size": "$unique_sets"} 
        }
    },
    {"$sort": {"num_sets": 1}}, 
    {"$limit": 1}  
    ])

    user_with_less_sets = next(user_with_less_sets, None)

    most_frequent_part = USERS_COLLECTION.aggregate([
    # Zamiana "parts" w "inventory.parts" na tablicę par klucz-wartość
    {"$project": {
        "parts": {"$objectToArray": "$inventory.parts"}
    }},
    {"$unwind": "$parts"},  # Rozwijamy tablicę, aby przetwarzać każdy klocek
    {
        "$group": {
            "_id": "$parts.k",  # Grupujemy po ID części (klucz)
            "count": {"$sum": 1}  # Liczymy ile razy pojawia się każda część
        }
    },
    {"$sort": {"count": -1}},  # Sortujemy według liczby wystąpień w malejącej kolejności
    {"$limit": 1}  # Zwracamy tylko najczęściej występujący klocek
    ])

    most_frequent_part = next(most_frequent_part, None)

    less_frequent_part = USERS_COLLECTION.aggregate([
    {"$project": {
        "parts": {"$objectToArray": "$inventory.parts"}
    }},
    {"$unwind": "$parts"},  {
        "$group": {
            "_id": "$parts.k", 
            "count": {"$sum": 1}  
        }
    },
    {"$sort": {"count": 1}},  
    {"$limit": 1} 
    ])
    less_frequent_part = next(less_frequent_part, None)

    most_frequent_set = USERS_COLLECTION.aggregate([
    {"$project": {
        "sets": {"$objectToArray": "$inventory.sets"}
    }},
    {"$unwind": "$sets"}, 
    {
        "$group": {
            "_id": "$sets.k", 
            "count": {"$sum": 1}  
        }
    },
    {"$sort": {"count": -1}}, 
    {"$limit": 1}  
    ])
    most_frequent_set = next(most_frequent_set, None)

    less_frequent_set = USERS_COLLECTION.aggregate([
    {"$project": {
        "sets": {"$objectToArray": "$inventory.sets"}
    }},
    {"$unwind": "$sets"}, 
    {
        "$group": {
            "_id": "$sets.k", 
            "count": {"$sum": 1}  
        }
    },
    {"$sort": {"count": 1}}, 
    {"$limit": 1}  
    ])
    less_frequent_set = next(less_frequent_set, None)

    
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
    statistics['parts'] = {
        "total_parts": total_parts,
        "colors_distribution": colors_distribution,
        "part_with_less_offers": part_with_less_offers,
        "part_with_most_offers": part_with_most_offers,
        "cheapest_part": cheapest_part,
        "most_expensive_part": most_expensive_part
    }

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

    return jsonify(statistics)
