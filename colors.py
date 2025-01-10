from flask import Flask
from flask import Blueprint
from imports import *

colors_api = Blueprint('colors_api', __name__)
COLORS_COLLECTION = DB['colors']

@colors_api.route('')
@redis_cache(module='colors')
def get_colors():
    result = list(COLORS_COLLECTION.find())
    for color in result:
        color['_id'] = str(color['_id'])
    return jsonify(result) 

@colors_api.route('/<id>')
@redis_cache(module='colors')
def get_color(id):
    result = list(COLORS_COLLECTION.find({"_id": int(id)}))
    if not result:
        return jsonify({'error': 'Color not found'}), 404
    return jsonify(result) 

# TODO add new color (include id in request)
@colors_api.route('', methods=['POST'])
@redis_cache(module='colors')
def add_color():
    try:
        # Pobranie danych wejściowych
        new_color = request.get_json()

        # Walidacja danych wejściowych
        if not isinstance(new_color, dict):
            return jsonify({'error': 'Input must be a JSON object'}), 400
        if '_id' not in new_color or not str(new_color['_id']).isdigit():
            return jsonify({'error': 'Invalid input: "_id" is required and must be an integer or a string representing an integer'}), 400
        if 'name' not in new_color or 'rgb' not in new_color:
            return jsonify({'error': 'Invalid input: "name" and "rgb" fields are required'}), 400

        # Konwersja _id na int przed zapisaniem
        new_color['_id'] = int(new_color['_id'])

        # Sprawdzenie, czy kolor o podanym `_id` już istnieje
        existing_color = COLORS_COLLECTION.find_one({'_id': new_color['_id']})
        if existing_color:
            return jsonify({'error': f'Color with _id {new_color["_id"]} already exists'}), 409

        # Wstawienie nowego koloru do kolekcji
        COLORS_COLLECTION.insert_one(new_color)

        # Konwersja `_id` z powrotem na string w odpowiedzi
        new_color['_id'] = str(new_color['_id'])

        # Zwrócenie odpowiedzi bez krotki
        response = jsonify(new_color)
        response.status_code = 201
        return response

    except Exception as e:
        # Obsługa wyjątków
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@colors_api.route('/<id>', methods=['PUT'])
@redis_cache(module='colors')
def update_color(id):
    updated_data = request.get_json()

    # Validate input data
    if not isinstance(updated_data, dict):
        return jsonify({'error': 'Input must be a JSON object'}), 400

    try:
        # Update color in the database
        result = COLORS_COLLECTION.update_one({"_id": int(id)}, {"$set": updated_data})

        if result.matched_count == 0:
            return jsonify({'error': 'Color not found'}), 404

        # Retrieve the updated color
        updated_color = COLORS_COLLECTION.find_one({"_id": int(id)})
        updated_color['_id'] = str(updated_color['_id'])

        response = jsonify({'message': 'Color updated successfully', 'color': updated_color})
        response.status_code = 200
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@colors_api.route('/<id>', methods=['DELETE'])
@redis_cache(module='colors')
def delete_color(id):
    try:
        # Attempt to delete the color
        result = COLORS_COLLECTION.delete_one({"_id": int(id)})

        if result.deleted_count == 0:
            return jsonify({'error': 'Color not found'}), 404
            
        response = jsonify({'message': 'Color deleted successfully'})
        response.status_code = 201
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
