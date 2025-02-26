from imports import *

parts_api = Blueprint('parts_api', __name__)
PARTS_COLLECTION = DB['parts']
COLORS_COLLECTION = DB['colors']

#collor maping 
def get_color_name_map():
    """uptake all colors and map them {id: name}."""
    return {str(color['_id']): color['name'] for color in COLORS_COLLECTION.find()}

@parts_api.route('')
def get_parts():
    limit = request.args.get('limit', default=25, type=int)

    @redis_cache(module='parts', expire=600, limit=limit)
    def sub_get_parts():
        result = list(PARTS_COLLECTION.find().limit(limit))
        new_res = []
        for part in result:
            part['_id'] = str(part['_id'])
            part['colors'] = [k for k in part['colors'].keys()]
            new_res.append(part)
        return jsonify(new_res), 200
    
    return sub_get_parts()


@parts_api.route('/<id>')
@redis_cache(module='parts', expire=60)
def get_part(id):
    color_map = get_color_name_map()
    result = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not result:
        return jsonify({'error': 'Part not found'}), 404
    
    return jsonify(result), 200

@parts_api.route('/colors/<color>')
def get_parts_by_color(color):
    limit = request.args.get('limit', default=25, type=int)

    @redis_cache(module='parts', expire=60, limit=limit)
    def sub_get_by_color(color):
        
        if not limit:
            return jsonify({'error': 'Invalid limit value. Must be an integer.'}), 400
        
        aggregation = [
            {
                '$match': {
                    f'colors.{color}': {
                        '$exists': True
                    }
                }
            }, {
                '$project': {
                    'colors': {
                        color: 1
                    }
                }
            },
            {'$limit': int(limit)}
        ]

        
        return jsonify(list(PARTS_COLLECTION.aggregate(aggregation))), 200
    
    return sub_get_by_color(color)

def validate_part_data(data, is_update=False):
    if not isinstance(data, dict):
        return "Invalid input. JSON body is required."
    
    required_fields = ['colors'] if is_update else ['_id', 'colors']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    
    if any(key not in required_fields for key in data.keys()):
        return "Invalid fields detected. Only '_id' and 'colors' are allowed."
    
    if not isinstance(data['colors'], dict):
        return jsonify({'error': "'colors' must be a dictionary with color ids as keys and arrays of objects as values."}), 400

        if not isinstance(offers, list):
            return f"'{color_key}' should have a list of offers."
        
        for offer in offers:
            if not isinstance(offer, dict):
                return jsonify({'error': f"Each offer for color '{color}' should be a dictionary."}), 400

            if 'Link' in offer:
                if 'Price' not in offer or 'Quantity' not in offer:
                    return jsonify({'error': f"If a 'Link' is provided for color '{color}', both 'Price' and 'Quantity' must be present."}), 400
                
                if not isinstance(offer['Price'], (int, float)):
                    return jsonify({'error': f"The 'Price' in offer for color '{color}' must be a number."}), 400
                if not isinstance(offer['Quantity'], int):
                    return jsonify({'error': f"The 'Quantity' in offer for color '{color}' must be an integer."}), 400
            else:
                if 'Price' in offer or 'Quantity' in offer:
                    return jsonify({'error': f"If no 'Link' is provided for color '{color}', 'Price' and 'Quantity' cannot be specified."}), 400

    result = PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({'error': 'Part not found'}), 404

    return jsonify({'modified_count': result.modified_count}), 200


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
        return jsonify({'error': "'colors' must be a dictionary with color id as keys and arrays of objects as values."}), 400

@parts_api.route('/<id>', methods=['PUT'])
def update_part(id):
    data = request.json
    error_message = validate_part_data(data, is_update=True)
    if error_message:
        return jsonify({'error': error_message}), 400
    
    data['_id'] = str(id)
    try:
        result = PARTS_COLLECTION.update_one({"_id": id}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({'error': 'Part not found'}), 404
        return jsonify({'modified_count': result.modified_count})
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500

@parts_api.route('', methods=['POST'])
def create_part():
    data = request.json
    error_message = validate_part_data(data)
    if error_message:
        return jsonify({'error': error_message}), 400
    
    try:
        result = PARTS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 200
    except DuplicateKeyError:
        return jsonify({'error': f"Part with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500


@parts_api.route('/<id>', methods=['DELETE'])
def delete_part(id):
    result = PARTS_COLLECTION.delete_one({"_id": str(id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Part not found'}), 404
    return jsonify({'deleted_count': result.deleted_count}), 200

@parts_api.route('/offers/<id>/<color>', methods=['GET'])
@redis_cache(module='parts', expire=60)
def get_offers_by_color(id, color):
    color = color.lower()
    color_map = {v.lower(): k for k, v in get_color_name_map().items()}  # Odwrócona mapa
    
    if color not in color_map:
        return jsonify({'error': f'Color "{color}" not found'}), 404
    
    color_id = color_map[color]

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    colors = part['colors']

    if color not in colors:
        return jsonify({'error': f'No offers found for color "{color}"'}), 404

    offers = colors[color]
    return jsonify(offers), 200

@parts_api.route('/<id>/colors', methods=['GET'])
@redis_cache(module='parts', expire=60)
def get_part_overview(id):
    color_map = get_color_name_map()
    part = PARTS_COLLECTION.find_one({"_id": str(id)}, {"_id": 1, "colors": 1})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    color_names = [color_map.get(str(color_id), f"Unknown ({color_id})") for color_id in part['colors'].keys()]

    return jsonify({
        "_id": part["_id"],
        "colors": color_names
    })


@parts_api.route('/<id>/colors', methods=['POST'])
def add_colors_to_part(id):
    data = request.json

    if not data or 'colors' not in data:
        return jsonify({'error': "'colors' field is required."}), 400

    colors_input = data['colors']
    if isinstance(colors_input, str):
        colors_to_add = [colors_input.strip().capitalize()]
    elif isinstance(colors_input, list) and all(isinstance(color, str) for color in colors_input):
        colors_to_add = [str(colors_input) for color in colors_input]
    else:
        return jsonify({'error': "'colors' must be a string or a list of strings."}), 400

    # Pobieramy mapę {name: _id}
    color_map = {v.capitalize(): str(k) for k, v in get_color_name_map().items()}
    
    # Sprawdzamy, czy podane kolory istnieją
    color_ids_to_add = {color_map[color] for color in colors_to_add if color in color_map}
    
    if not color_ids_to_add:
        return jsonify({'error': 'No valid colors found in database.'}), 400

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    part_colors = part.get('colors', {})
    existing_colors = part_colors.keys()

    new_colors = {color_id: [] for color_id in color_ids_to_add if color_id not in part_colors}

    if not new_colors:
        return jsonify({'message': 'No new colors to add. All colors already exist.'}), 400

    part_colors.update(new_colors)

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part_colors}})

    return jsonify({'message': f'Colors added to part: {", ".join(new_colors)}.'}), 200


@parts_api.route('/<id>/colors', methods=['DELETE'])
def delete_colors_from_part(id):
    data = request.json

    if not data or 'colors' not in data:
        return jsonify({'error': "'colors' field is required."}), 400

    colors_input = data['colors']
    if isinstance(colors_input, str):
        colors_to_delete = [colors_input.strip().capitalize()]
    elif isinstance(colors_input, list) and all(isinstance(color, str) for color in colors_input):
        colors_to_delete = [str(color) for color in colors_input]
    else:
        return jsonify({'error': "'colors' field must be a string or a list of strings."}), 400

    # Pobieramy mapę {name: _id}
    color_map = {v.capitalize(): str(k) for k, v in get_color_name_map().items()}
    
    # Zamieniamy nazwy na `_id`
    color_ids_to_delete = {color_map[color] for color in colors_to_delete if color in color_map}

    if not color_ids_to_delete:
        return jsonify({'error': 'No valid colors found in database.'}), 400

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    part_colors = part.get('colors', {})

    colors_removed = [color_id for color_id in color_ids_to_delete if color_id in part_colors]

    if not colors_removed:
        return jsonify({'message': 'No matching colors found to delete.'}), 404

    for color_id in colors_removed:
        del part_colors[color_id]

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part_colors}})

    removed_color_names = [color for color, color_id in color_map.items() if color_id in colors_removed]
    
    return jsonify({'message': f'Colors deleted from part: {", ".join(removed_color_names)}.'}), 200

@parts_api.route('/<id>/offers', methods=['POST'])
def add_offer_to_part(id):
    data = request.json

    if not data or 'colors' not in data:
        return jsonify({'error': "'colors' field is required."}), 400

    colors = data['colors']

    if not isinstance(colors, dict):
        return jsonify({'error': "'colors' must be a dictionary with color ids as keys and lists of offers as values."}), 400

    for color, offers in colors.items():
        if not isinstance(offers, list):
            return jsonify({'error': f"'{color}' should have a list of offers."}), 400

        for offer in offers:
            if not isinstance(offer, dict) or 'Link' not in offer or 'Price' not in offer or 'Quantity' not in offer:
                return jsonify({'error': f"Each offer for color '{color}' must include 'Link', 'Price', and 'Quantity'."}), 400

            if not isinstance(offer['Price'], (int, float)):
                return jsonify({'error': f"The 'Price' in offer for color '{color}' must be a number."}), 400
            if not isinstance(offer['Quantity'], int):
                return jsonify({'error': f"The 'Quantity' in offer for color '{color}' must be an integer."}), 400

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    if 'colors' not in part:
        part['colors'] = {}

    for color, offers in colors.items():
        if color not in part['colors']:
            part['colors'][color] = []

        part['colors'][color].extend(offers)
        part['colors'][color].sort(key=lambda x: x['Price'])

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part['colors']}})

    return jsonify({'message': 'Offers added successfully.'}), 200

@parts_api.route('/<id>/offers', methods=['DELETE'])
def delete_offer_from_part(id):
    data = request.json

    # Validate input: both 'color' and 'link' fields are required
    if not data or 'color' not in data or 'link' not in data:
        return jsonify({'error': "'color' (single color) and 'link' fields are required."}), 400

    color_input = data['color']
    link = data['link'].strip().lower()

    # Fetch color mapping {_id: name} and {name: _id} from the COLORS_COLLECTION
    color_map_id_to_name = get_color_name_map()
    color_map_name_to_id = {v: k for k, v in color_map_id_to_name.items()}

    if isinstance(color_input, str):
        color = color_input.strip()
    else:
        return jsonify({'error': f"Invalid color: '{color_input}'. It must be a valid name or existing ID in the database."}), 400

    # Retrieve the part from the database
    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    # Ensure the part has a 'colors' field
    part_colors = part.get('colors', {})
    if not part_colors:
        return jsonify({'error': 'No colors found in this part.'}), 404

    # Check if the specified color exists in the part
    if color_id not in part_colors:
        return jsonify({'error': f"Color '{color_map_id_to_name.get(color_id, color_id)}' not found in this part."}), 404

    # Find the offer to remove by matching the link
    offers = part_colors[color_id]
    offer_to_remove = next((offer for offer in offers if offer.get('Link', '').strip().lower() == link), None)

    if not offer_to_remove:
        return jsonify({'error': f"Offer with the specified link not found in color '{color_map_id_to_name.get(color_id, color_id)}'."}), 404

    # Remove the offer
    part_colors[color_id].remove(offer_to_remove)

    # If no offers remain for the color, keep an empty list (avoid deleting the color entry)
    if not part_colors[color_id]:
        part_colors[color_id] = []

    # Sort the remaining offers by price (ascending) and quantity (descending)
    part_colors[color_id].sort(key=lambda x: (x.get('Price', float('inf')), -x.get('Quantity', 0)))

    # Update the part in the database
    update_result = PARTS_COLLECTION.update_one(
        {"_id": str(id)},
        {"$set": {"colors": part_colors}}
    )

    if update_result.modified_count == 0:
        return jsonify({'error': 'Failed to update the part in the database.'}), 500

    return jsonify({'message': f"Offer deleted from color '{color_map_id_to_name.get(color_id, color_id)}'."}), 200
