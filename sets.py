from imports import *

sets_api = Blueprint('sets_api', __name__)
SET_OVERVIEWS_COLLECTION = DB['set_overviews']
SET_OFFERS_COLLECTION = DB['set_offers']
SET_SIMILARITIES_COLLECTION = DB['set_similarities']
SET_CONTENTS_COLLECTION = DB['set_contents']
PARTS_COLLECTION = DB['parts']

@sets_api.route('')
@redis_cache(module='colors', expire=600)
def get_sets():
    result = list(SET_OVERVIEWS_COLLECTION.find())
    for set in result:
        set['_id'] = str(set['_id'])    
    return jsonify(result)

@sets_api.route('/<id>')
@redis_cache(module='sets', expire=600)
def get_set(id):
    result = SET_OVERVIEWS_COLLECTION.find_one({"_id": str(id)})
    offers = SET_OFFERS_COLLECTION.find_one({"_id": str(id)})
    contents = SET_CONTENTS_COLLECTION.find_one({"_id": str(id)})

    if not result:
        return jsonify({'error': 'Set not found.'}), 404

    result = result | contents
    if offers:
        result = result | offers
    
    # if result:
    #     REDIS.hincrby(f"set:{id}", "visit_count", 1)
    return jsonify(result)

@sets_api.route('/<id>/offers', methods=['PUT', 'POST'])
def update_set_offers(id):
    data = request.json
    print('dupa')

    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid input. JSON array body is required.'}), 400
    
    for offer in data:
        if not isinstance(offer, dict):
            return jsonify({'error': 'Invalid input. JSON array must contain objects.'}), 400
        if 'link' not in offer or 'price' not in offer:
            return jsonify({'error': 'Missing required fields: link, price.'}), 400
        if not isinstance(offer['price'], (float, int)):
            print(offer['price'], type(offer['price']))
            return jsonify({'error': 'Price must be a float.'}), 400
    
    min_price = data[0]["price"]

    r1 = SET_OVERVIEWS_COLLECTION.update_one({"_id": id}, {"$set": {"min_price": min_price}}, upsert=True)
    result = SET_OFFERS_COLLECTION.update_one({"_id": id}, {"$set": {"offers": data}}, upsert=True)

    return jsonify(r1.modified_count, result.modified_count)

@sets_api.route('', methods=['POST'])
def create_set():
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    required_fields = ['_id', 'name', 'year', 'num_parts', 'parts']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    if not isinstance(data['parts'], dict):
        return jsonify({'error': "'parts' must be a dictionary with part IDs as keys and objects as values."}), 400

    # Very time consuming part here, but at the same time, scarecely used
    sim_scores = []
    part_keys = data['parts'].keys()
    for other_set_contents in SET_CONTENTS_COLLECTION.find():
        parts_in_common = 0
        for other_part in other_set_contents.items():
            if other_part[0] in part_keys:
                if other_set_contents[1]['color'] in data['parts'][other_part[0]]['colors']:
                    parts_in_common += min(other_set_contents['quantity'], data['parts'][other_part[0]]['quantity'])
        if parts_in_common > 0:
            total_parts = len(other_set_contents)
            sim_score = round(parts_in_common / total_parts, 2)
            sim_scores.append((other_set_contents["_id"], sim_score))
            SET_SIMILARITIES_COLLECTION.update_one(
                {"_id": other_set_contents["_id"]},
                {"$push": {"sim_scores": {"_id": data["_id"], "sim_score": sim_score}}},
                upsert=True
            )

    if not isinstance(data['sim_scores'], list):
        return jsonify({'error': "'sim_scores' must be a list."}), 400

    for part_id, part_data in data['parts'].items():
        existing_part = PARTS_COLLECTION.find_one({"_id": part_id})
        if not existing_part:
            try:
                part_data["_id"] = part_id  
                PARTS_COLLECTION.insert_one(part_data)
            except DuplicateKeyError:
                pass 
    
    try:
        SET_OFFERS_COLLECTION.insert_one({"_id": data["_id"], "offers": []})
    except DuplicateKeyError:
        return jsonify({'error': f"Set offers with _id '{data['_id']}' already exist."}), 409

    try: 
        SET_CONTENTS_COLLECTION.insert_one({"_id": data["_id"], "parts": data["parts"]})
    except DuplicateKeyError:
        return jsonify({'error': f"Set contents with _id '{data['_id']}' already exist."}), 409
    
    try:
        SET_SIMILARITIES_COLLECTION.insert_one({"_id": data["_id"], "sim_scores": data["sim_scores"]})
    except DuplicateKeyError:
        return jsonify({'error': f"Similarity score with _id '{data['_id']}' already exists."}), 409

    try:
        del data['parts']
        result = SET_OVERVIEWS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 201
    except DuplicateKeyError:
        return jsonify({'error': f"Set with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500

@sets_api.route('/<id>', methods=['DELETE'])
def delete_set(id):
    result = SET_OVERVIEWS_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Set not found'}), 404
    
    result = SET_SIMILARITIES_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Set not found'}), 404
    
    result = SET_OFFERS_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Set not found'}), 404
    
    result = SET_CONTENTS_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Set not found'}), 404
    
    return jsonify({'deleted_count': result.deleted_count})

@sets_api.route('/profitable/<x>')
@redis_cache(module='colors', expire=60)
def get_profitable_sets(x):
    pipeline = [
        {
            "$match": {
                "min_offer": {
                    "$exists": True,
                },
                "price": {
                    "$exists": True
                }
            }
        },
        {
            "$addFields": {
                "difference": {
                    "$subtract": [
                        "$price",
                        "$min_offer"
                    ]
                }
            }
        },
        {
            "$sort": {
                "difference": -1
            }
        },
        {
            "$project": {
                "difference": 0
            }
        },
        {
            "$limit": int(x)
        }
    ]
        
    top_sets = list(SET_OVERVIEWS_COLLECTION.aggregate(pipeline))
    return top_sets

@sets_api.route('/popular/<x>')
@redis_cache(module='colors', expire=60)
def get_popular_sets(x):
    all_sets = REDIS.smembers("all_sets")
    popular_sets = []
    for set_key in all_sets:
        visit_count = REDIS.hget(set_key, "visit_count")
        popular_sets.append({"_id": set_key.split(":")[1], "visit_count": visit_count})
    popular_sets = sorted(popular_sets, key=lambda x: x['visit_count'], reverse=True)[:int(x)]
    result = []
    for s in popular_sets:
        result.append(SET_OVERVIEWS_COLLECTION.find_one({"_id": s["_id"]}))
    return jsonify(result)

@sets_api.route('/cheapest/new/<x>')
@redis_cache(module='colors', expire=60)
def get_cheapest_new_sets(x):
    result = SET_OVERVIEWS_COLLECTION.find({"price": {"$ne": None}}).sort("price", 1).limit(int(x))
    return jsonify(list(result))

@sets_api.route('/cheapest/used/<x>')
@redis_cache(module='colors', expire=60)
def get_cheapest_used_sets(x):
    pipeline = [
        {
            "$match": {
                "min_offer": {
                    "$exists": True
                }
            }
        },
        {
            "$sort": {
                "min_price": 1
            }
        },
        {
            "$limit": int(x)
        }
    ]

    top_sets = list(SET_OVERVIEWS_COLLECTION.aggregate(pipeline))
    return top_sets
