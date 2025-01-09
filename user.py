from flask import Blueprint
from imports import *

users_api = Blueprint('users_api', __name__)
USERS_COLLECTION = DB['users']

@users_api.route('')
def get_users():
    result = list(USERS_COLLECTION.find())
    for user in result:
        user['_id'] = str(user['_id'])
    return jsonify(result)

@users_api.route('/', methods=['POST'])
def create_user():
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    required_fields = ['_id', 'password']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    if 'is_admin' not in data:
        data['is_admin'] = False

    data['inventory'] = {
        'parts': {},
        'sets': {}
    }

    try:
        result = USERS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 201
    except DuplicateKeyError:
        return jsonify({'error': f"Part with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500

@users_api.route('/<id>')
def get_user(id):
    result = list(USERS_COLLECTION.find({"_id": id}))
    if not result:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(result)

@users_api.route('/<id>/inventory')
def get_user_inventory(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return None
    return user['inventory']

@users_api.route('/<id>/inventory', methods=['POST'])
def add_items_to_inventory(id):
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    if 'parts' in data and not isinstance(data['parts'], dict):
        return jsonify({'error': "'parts' must be a dictionary with part IDs as keys, colors and quantities as values."}), 400

    if 'sets' in data and not isinstance(data['sets'], dict):
        return jsonify({'error': "'sets' must be a dictionary with set IDs as keys and quantities as values."}), 400

    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    for part_id, quantity in data.get('parts', {}).items():
        if part_id not in user['inventory']['parts']:
            user['inventory']['parts'][part_id] = 0
        user['inventory']['parts'][part_id] += quantity

    for set_id, quantity in data.get('sets', {}).items():
        if set_id not in user['inventory']['sets']:
            user['inventory']['sets'][set_id] = 0
        user['inventory']['sets'][set_id] += quantity

    result = USERS_COLLECTION.update_one({"_id": id}, {"$set": user})

    if result.matched_count == 0:
        return jsonify({'error': 'Operation failed'}), 400

    return jsonify({USERS_COLLECTION.find_one({"_id": id})['inventory']})

@users_api.route('/<id>/inventory', methods=['DELETE'])
def remove_items_from_inventory(id):
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    if 'parts' in data and not isinstance(data['parts'], dict):
        return jsonify({'error': "'parts' must be a dictionary with part IDs as keys, colors and quantities as values."}), 400

    if 'sets' in data and not isinstance(data['sets'], dict):
        return jsonify({'error': "'sets' must be a dictionary with set IDs as keys and quantities as values."}), 400
    
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    for part_id, quantity in data.get('parts', {}).items():
        if part_id not in user['inventory']['parts']:
            return jsonify({'error': f"Part with ID '{part_id}' not found in user's inventory."}), 404
        user['inventory']['parts'][part_id] -= quantity
        if user['inventory']['parts'][part_id] <= 0:
            del user['inventory']['parts'][part_id]

    for set_id, quantity in data.get('sets', {}).items():
        if set_id not in user['inventory']['sets']:
            return jsonify({'error': f"Set with ID '{set_id}' not found in user's inventory."}), 404
        user['inventory']['sets'][set_id] -= quantity
        if user['inventory']['sets'][set_id] <= 0:
            del user['inventory']['sets'][set_id]