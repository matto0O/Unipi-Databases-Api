from flask import Blueprint
from imports import *

sets_api = Blueprint('sets_api', __name__)
SETS_COLLECTION = DB['sets']
PARTS_COLLECTION = DB['parts']

@sets_api.route('')
def get_sets():
    result = list(SETS_COLLECTION.find())
    for set in result:
        set['_id'] = str(set['_id'])    
    return jsonify(result)

@sets_api.route('/<id>')
@redis_cache(module='sets')
def get_set(id):
    result = list(SETS_COLLECTION.find({"_id": str(id)}))
    if result:
        REDIS.hincrby(f"set:{id}", "visit_count", 1)
    return jsonify(result)

@sets_api.route('/<id>', methods=['PUT'])
def update_set(id):
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    if 'parts' in data and not isinstance(data['parts'], dict):
        return jsonify({'error': "'parts' must be a dictionary with part IDs as keys and objects as values."}), 400

    if 'sim_scores' in data and not isinstance(data['sim_scores'], list):
        return jsonify({'error': "'sim_scores' must be a list."}), 400

    result = SETS_COLLECTION.update_one({"_id": id}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({'error': 'Set not found.'}), 404

    return jsonify({'modified_count': result.modified_count})


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
        result = SETS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 201
    except DuplicateKeyError:
        return jsonify({'error': f"Set with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500

@sets_api.route('/<id>', methods=['DELETE'])
def delete_set(id):
    result = SETS_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Set not found'}), 404
    return jsonify({'deleted_count': result.deleted_count})

# TODO add/delete a new offer for a set

# TODO on set creation count similarity scores with other sets and add only sets that have at least one part in common


# TODO find most profitable sets

@sets_api.route('/popular/<x>')
def get_popular_sets(x):
    all_sets = REDIS.smembers("all_sets")
    popular_sets = []
    for set_key in all_sets:
        visit_count = REDIS.hget(set_key, "visit_count")
        popular_sets.append({"_id": set_key.split(":")[1], "visit_count": visit_count})
    popular_sets = sorted(popular_sets, key=lambda x: x['visit_count'], reverse=True)[:int(x)]
    result = []
    for s in popular_sets:
        result.append(SETS_COLLECTION.find_one({"_id": s["_id"]}))
    return jsonify(result)

# TODO find top x cheapest sets