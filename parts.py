from flask import Blueprint
from imports import *

parts_api = Blueprint('parts_api', __name__)
PARTS_COLLECTION = DB['parts']

@parts_api.route('')
def get_parts():
    result = list(PARTS_COLLECTION.find())
    for part in result:
        part['_id'] = str(part['_id'])
    return jsonify(result)

@parts_api.route('/<id>')
def get_part(id):
    result = list(PARTS_COLLECTION.find({"_id": str(id)}))
    if not result:
        return jsonify({'error': 'Part not found'}), 404
    return jsonify(result)

@parts_api.route('/<id>', methods=['PUT'])
def update_part(id):
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    required_fields = ['colors']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    if not isinstance(data['colors'], dict):
        return jsonify({'error': "'colors' must be a dictionary with color names as keys and arrays of objects as values."}), 400

    result = PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({'error': 'Part not found'}), 404
    return jsonify({'modified_count': result.modified_count})

@parts_api.route('', methods=['POST'])
def create_part():
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    required_fields = ['_id', 'colors']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    if not isinstance(data['colors'], dict):
        return jsonify({'error': "'colors' must be a dictionary with color names as keys and arrays of objects as values."}), 400

    try:
        result = PARTS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 201
    except DuplicateKeyError:
        return jsonify({'error': f"Part with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500


@parts_api.route('/<id>', methods=['DELETE'])
def delete_part(id):
    result = PARTS_COLLECTION.delete_one({"_id": str(id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Part not found'}), 404
    return jsonify({'deleted_count': result.deleted_count})   