from imports import *

colors_api = Blueprint('colors_api', __name__)

@colors_api.route('')
@redis_cache(module='colors')
def get_colors():
    results = []
    for key in REDIS.keys("colors:*"):
        values = REDIS.hgetall(key)
        values["_id"] = key.split(":")[1]
        results.append(values)
    return jsonify(results), 200

@colors_api.route('/<id>')
@redis_cache(module='colors')
def get_color(id):
    result = REDIS.hgetall(f'colors:{id}')
    result["_id"] = id
    if not result:
        return jsonify({'error': 'Color not found'}), 404
    return jsonify(result), 200

#  add new color (include id in request)
@colors_api.route('', methods=['POST'])
def add_color():
    try:
        new_color = request.get_json()

        if not isinstance(new_color, dict):
            return jsonify({'error': 'Input must be a JSON object'}), 400
        if '_id' not in new_color or not str(new_color['_id']).isdigit():
            return jsonify({'error': 'Invalid input: "_id" is required and must be an integer or a string representing an integer'}), 400
        if 'name' not in new_color or 'rgb' not in new_color:
            return jsonify({'error': 'Invalid input: "name" and "rgb" fields are required'}), 400

        new_color['_id'] = int(new_color['_id'])

        existing_color = REDIS.keys(f'colors:{new_color["_id"]}')
        if existing_color:
            return jsonify({'error': f'Color with _id {new_color["_id"]} already exists'}), 409

        REDIS.hmset(f'colors:{new_color["_id"]}', new_color)

        new_color['_id'] = str(new_color['_id'])
        return jsonify(new_color), 200

    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@colors_api.route('/<id>', methods=['PUT'])
def update_color(id):
    updated_data = request.get_json()

    if not isinstance(updated_data, dict):
        return jsonify({'error': 'Input must be a JSON object'}), 400

    try:
        REDIS.hmset(f'colors:{id}', updated_data)
        return jsonify({'message': 'Color updated successfully', 'color': id}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@colors_api.route('/<id>', methods=['DELETE'])
def delete_color(id):
    try:
        REDIS.hdel(f'colors:{id}')
        return jsonify({'message': 'Color deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
