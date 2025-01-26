from imports import *

parts_api = Blueprint('parts_api', __name__)
PARTS_COLLECTION = DB['parts']

@parts_api.route('')
def get_parts():
    result = list(PARTS_COLLECTION.find())
    for part in result:
        part['_id'] = str(part['_id'])
        part['colors'] = {color.capitalize(): value for color, value in part['colors'].items()}

    return jsonify(result)

@parts_api.route('/<id>')
def get_part(id):
    result = list(PARTS_COLLECTION.find({"_id": str(id)}))
    if not result:
        return jsonify({'error': 'Part not found'}), 404
    
    for part in result:
        part['_id'] = str(part['_id'])
        part['colors'] = {color.capitalize(): value for color, value in part['colors'].items()}
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

    # Normalize colors directly in the method
    normalized_colors = {}
    for color, offers in data['colors'].items():
        normalized_color = color.capitalize()  
        normalized_colors[normalized_color] = offers

    data['colors'] = normalized_colors

    for color, offers in data['colors'].items():
        if not isinstance(offers, list):
            return jsonify({'error': f"'{color}' should have a list of offers."}), 400

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

    return jsonify({'modified_count': result.modified_count})

# Route to create a new part
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

    # Normalizacja kolorów bezpośrednio w metodzie
    normalized_colors = {}
    for color, offers in data['colors'].items():
        normalized_color = color.capitalize()  # Normalizowanie koloru na pierwszą wielką literę
        normalized_colors[normalized_color] = offers

    data['colors'] = normalized_colors

    for color, offers in data['colors'].items():
        if not isinstance(offers, list):
            return jsonify({'error': f"'{color}' should have a list of offers."}), 400

        for offer in offers:
            if not isinstance(offer, dict):
                return jsonify({'error': f"Each offer for color '{color}' should be a dictionary."}), 400

            if 'Link' not in offer or 'Price' not in offer or 'Quantity' not in offer:
                return jsonify({'error': f"Each offer for color '{color}' must include 'Link', 'Price', and 'Quantity'."}), 400

            if not isinstance(offer['Price'], (int, float)):
                return jsonify({'error': f"The 'Price' in offer for color '{color}' must be a number."}), 400
            if not isinstance(offer['Quantity'], int):
                return jsonify({'error': f"The 'Quantity' in offer for color '{color}' must be an integer."}), 400

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

@parts_api.route('/offers/<id>/<color>', methods=['GET'])
def get_offers_by_color(id, color):
    color = color.lower()
    part = PARTS_COLLECTION.find_one({"_id": str(id)})
    
    if not part:
        return jsonify({'error': 'Part not found'}), 404

    colors = {k.lower(): v for k, v in part['colors'].items()}

    if color not in colors:
        return jsonify({'error': f'No offers found for color "{color}"'}), 404

    offers = colors[color]
    return jsonify(offers)

@parts_api.route('/<id>/colors', methods=['GET'])
def get_part_overview(id):
    part = PARTS_COLLECTION.find_one({"_id": str(id)}, {"_id": 1, "colors": 1})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    color_names = list(part['colors'].keys())

    return jsonify({
        "_id": part["_id"],
        "colors": color_names
    })

@parts_api.route('/<id>/colors', methods=['POST'])
def add_colors_to_part(id):
    data = request.json

    if not data or not any(k.lower() == 'colors' for k in data):
        return jsonify({'error': "'colors' field is required."}), 400

    colors_input = next((data[k] for k in data if k.lower() == 'colors'), None)

    if isinstance(colors_input, str):
        colors_to_add = [colors_input.strip().capitalize()]
    elif isinstance(colors_input, list) and all(isinstance(color, str) for color in colors_input):
        colors_to_add = [color.strip().capitalize() for color in colors_input]
    else:
        return jsonify({'error': "'colors' must be a string or a list of strings."}), 400

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    part_colors = part.get('colors', {})
    existing_colors = {color.capitalize() for color in part_colors.keys()}

    new_colors = [color for color in colors_to_add if color not in existing_colors]

    if not new_colors:
        return jsonify({'message': 'No new colors to add. All colors already exist.'}), 400

    for color in new_colors:
        part_colors[color] = []

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part_colors}})

    return jsonify({'message': f'Colors added to part: {", ".join(new_colors)}.'}), 201



@parts_api.route('/<id>/colors', methods=['DELETE'])
def delete_colors_from_part(id):
    data = request.json

    if not data or not any(k.lower() == 'colors' for k in data):
        return jsonify({'error': "'colors' field is required."}), 400

    colors_input = next((data[k] for k in data if k.lower() == 'colors'), None)

    if isinstance(colors_input, str):
        colors_to_delete = [colors_input.strip().capitalize()]
    elif isinstance(colors_input, list) and all(isinstance(color, str) for color in colors_input):
        colors_to_delete = [color.strip().capitalize() for color in colors_input]
    else:
        return jsonify({'error': "'colors' field must be a string or a list of strings."}), 400

    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    part_colors = part.get('colors', {})
    if not part_colors:
        return jsonify({'message': 'No colors exist for this part.'}), 404

    colors_to_remove = []
    for color in colors_to_delete:
        matching_color = next((existing_color for existing_color in part_colors if existing_color.lower() == color.lower()), None)
        if matching_color:
            colors_to_remove.append(matching_color)

    if not colors_to_remove:
        return jsonify({'message': 'No matching colors found to delete.'}), 404

    for color in colors_to_remove:
        del part_colors[color]

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part_colors}})

    return jsonify({'message': f'Colors deleted from part: {", ".join(colors_to_remove)}.'}), 200

@parts_api.route('/<id>/offers', methods=['POST'])
def add_offer_to_part(id):
    data = request.json

    if not data or 'colors' not in data:
        return jsonify({'error': "'colors' field is required."}), 400

    colors = data['colors']

    if not isinstance(colors, dict):
        return jsonify({'error': "'colors' must be a dictionary with color names as keys and lists of offers as values."}), 400

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
        normalized_color = color.capitalize()
        if normalized_color not in part['colors']:
            part['colors'][normalized_color] = []

        part['colors'][normalized_color].extend(offers)
        part['colors'][normalized_color].sort(key=lambda x: x['Price'])

    PARTS_COLLECTION.update_one({"_id": str(id)}, {"$set": {"colors": part['colors']}})

    return jsonify({'message': 'Offers added successfully.'}), 201

@parts_api.route('/<id>/offers', methods=['DELETE'])
def delete_offer_from_part(id):
    data = request.json

    if not data or not any(k.lower() == 'color' for k in data) or not any(k.lower() == 'link' for k in data):
        return jsonify({'error': "'color' (single color) and 'link' fields are required."}), 400

    color_input = next((data[k] for k in data if k.lower() == 'color'), None)
    link = next((data[k] for k in data if k.lower() == 'link'), None)

    if isinstance(color_input, str):
        color = color_input.strip().capitalize()
    else:
        return jsonify({'error': "'color' must be a single string."}), 400

    # Find the part
    part = PARTS_COLLECTION.find_one({"_id": str(id)})

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    part_colors = next((part[k] for k in part if k.lower() == 'colors'), None)
    if not isinstance(part_colors, dict):
        return jsonify({'error': 'No colors found in this part.'}), 404

    if color not in part_colors:
        return jsonify({'error': f"Color '{color}' not found in this part."}), 404

    offers = part_colors[color]
    offer_to_remove = next((offer for offer in offers if offer.get('Link', '').lower() == link.lower()), None)

    if not offer_to_remove:
        return jsonify({'error': f"Offer with the specified link not found in color '{color}'."}), 404

    part_colors[color].remove(offer_to_remove)

    if not part_colors[color]:
        part_colors[color] = []

    part_colors[color].sort(key=lambda x: (x.get('Price', float('inf')), -x.get('Quantity', 0)))

    update_result = PARTS_COLLECTION.update_one(
        {"_id": str(id)},
        {"$set": {"colors": part_colors}}
    )

    if update_result.modified_count == 0:
        return jsonify({'error': 'Failed to update the part in the database.'}), 500

    return jsonify({'message': f"Offer deleted from color '{color}'."}), 200
