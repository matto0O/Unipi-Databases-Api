from imports import *

colors_api = Blueprint('colors_api', __name__)
# COLORS_COLLECTION = DB['colors']

@colors_api.route('')
def get_colors():
    keys = REDIS.keys("colors:*")
    results = {}
    for key in keys:
        _, id, attr = key.split(":")
        if id not in results:
            results[id] = {}
        if attr == "name":
            results[id]['name'] = REDIS.get(key)
        else:
            results[id]['rgb'] = REDIS.get(key)
    return jsonify(results)

@colors_api.route('/<id>')
def get_color(id):
    name = REDIS.get(f"colors:{id}:name")
    rgb = REDIS.get(f"colors:{id}:rgb")
    if not name or not rgb:
        return jsonify({'error': 'Color not found'}), 404
    return jsonify({'_id': id, 'name': name, 'rgb': rgb}) 

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

        name = REDIS.get(f"colors:{new_color['_id']}:name")
        rgb = REDIS.get(f"colors:{new_color['_id']}:rgb")
        if name or rgb:
            return jsonify({'error': f'Color with _id {new_color["_id"]} already exists'}), 409

        REDIS.set(f"colors:{new_color['_id']}:name", new_color['name'])
        REDIS.set(f"colors:{new_color['_id']}:rgb", new_color['rgb'])

        return "Color added successfully", 201

    except Exception as e:

        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@colors_api.route('/<id>', methods=['DELETE'])
def delete_color(id):
    try:
        r1 = REDIS.delete(f"colors:{id}:name")
        r2 = REDIS.delete(f"colors:{id}:rgb")

        if r1 == 0 and r2 == 0:
            return jsonify({'error': 'Color not found'}), 404
            
        response = jsonify({'message': 'Color deleted successfully'})
        response.status_code = 201
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
