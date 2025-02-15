from user import users_api
from parts import parts_api
from colors import colors_api
from sets import sets_api
from stats import stats_api
from imports import *

app = Flask(__name__)
app.register_blueprint(users_api, url_prefix='/users')
app.register_blueprint(parts_api, url_prefix='/parts')
app.register_blueprint(colors_api, url_prefix='/colors')
app.register_blueprint(sets_api, url_prefix='/sets')
app.register_blueprint(stats_api, url_prefix='/stats')

@app.route('/')
def index():
    return "Welcome to Brickscrapper"

# SETS
@app.route('/sets')
def get_sets():
    result = list(SETS_COLLECTION.find())
    for set in result:
        set['_id'] = str(set['_id'])    
    return flask.jsonify(result)

@app.route('/sets/<id>')
def get_set(id):
    result = list(SETS_COLLECTION.find({"_id": str(id)}))
    return flask.jsonify(result)

@app.route('/sets/<id>', methods=['PUT'])
def update_set(id):
    data = flask.request.json

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


@app.route('/sets', methods=['POST'])
def create_set():
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    required_fields = ['_id', 'name', 'year', 'num_parts', 'parts', 'sim_scores']
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

@app.route('/sets/<id>', methods=['DELETE'])
def delete_set(id):
    result = SETS_COLLECTION.delete_one({"_id": id})
    if result.deleted_count == 0:
        return flask.jsonify({'error': 'Set not found'}), 404
    return flask.jsonify({'deleted_count': result.deleted_count})

# COLORS
@app.route('/colors')
def get_colors():
    result = list(COLORS_COLLECTION.find())
    for color in result:
        color['_id'] = str(color['_id'])
    return flask.jsonify(result), 200

@app.route('/colors/<id>')
def get_color(id):
    result = list(COLORS_COLLECTION.find({"_id": int(id)}))
    if not result:
        return flask.jsonify({'error': 'Color not found'}), 404
    return flask.jsonify(result)

# PARTS
@app.route('/parts')
def get_parts():
    result = list(PARTS_COLLECTION.find())
    for part in result:
        part['_id'] = str(part['_id'])
    return flask.jsonify(result)

@app.route('/parts/<id>')
def get_part(id):
    result = list(PARTS_COLLECTION.find({"_id": str(id)}))
    if not result:
        return flask.jsonify({'error': 'Part not found'}), 404
    return flask.jsonify(result)

@app.route('/parts/<id>', methods=['PUT'])
def update_part(id):
    data = flask.request.json

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
        return flask.jsonify({'error': 'Part not found'}), 404
    return flask.jsonify({'modified_count': result.modified_count})

@app.route('/parts', methods=['POST'])
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


@app.route('/parts/<id>', methods=['DELETE'])
def delete_part(id):
    result = PARTS_COLLECTION.delete_one({"_id": str(id)})
    if result.deleted_count == 0:
        return flask.jsonify({'error': 'Part not found'}), 404
    return flask.jsonify({'deleted_count': result.deleted_count})

if __name__ == '__main__':
    app.run(debug=True)
