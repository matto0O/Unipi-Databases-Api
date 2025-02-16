from imports import *
import jwt
import datetime
from flask import current_app, jsonify, request
from functools import wraps

users_api = Blueprint('users_api', __name__)
USERS_COLLECTION = DB['users']
PARTS_COLLECTION = DB['parts']
SET_OVERVIEWS_COLLECTION = DB['set_overviews']
SET_CONTENTS_COLLECTION = DB['set_contents']
SET_SIMILARITIES_COLLECTION = DB['set_similiarities']
SET_OFFERS_COLLECTION = DB['set_offers']

# Making a token to authenticate users
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'No token!'}), 401
        try:
            token = token.replace('Bearer ', '')  # Remove 'Bearer ' prefix from token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = USERS_COLLECTION.find_one({'_id': data.get('_id')})
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        except Exception as e:
            return jsonify({'message': 'Authorization error', 'error': str(e)}), 401
        
        # If user is an admin, give access to everything
        if current_user.get('is_admin', False):
            return f(current_user, *args, **kwargs)

        # Otherwise, check if the user is trying to access their own data
        requested_user_id = kwargs.get('id')
        if current_user['_id'] != requested_user_id:
            return jsonify({'message': 'Unauthorized access'}), 403

        return f(current_user, *args, **kwargs)
    return decorated

# login
@users_api.route('/login', methods=['POST'])
def login():
    data = request.json
    print(f"Attempting login for username: {data.get('username')}")
    
    # Find the user in the database by username
    user = USERS_COLLECTION.find_one({'_id': data.get('username')})
    
    if user:
        print(f"Found user: {user}")
        # Check if the provided password matches the stored password
        if user['password'] == data.get('password'):
            # Generate a JWT token with user ID and expiration time
            token = jwt.encode(
                {'_id': user['_id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, 
                current_app.config['SECRET_KEY'], 
                algorithm='HS256'
            )
            return jsonify({'token': token})
        else:
            print("Incorrect password")
            return jsonify({'message': 'Invalid login credentials'}), 401
    else:
        print("User not found")
        return jsonify({'message': 'Invalid login credentials'}), 401


@users_api.route('')
@token_required
def get_users(current_user):    
    # chacking that curent user is the same as the user requested
    if not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
    
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
        'parts': [],
        'sets': []
    }
    try:
        result = USERS_COLLECTION.insert_one(data)
        return jsonify({'inserted_id': str(result.inserted_id)}), 201
    except DuplicateKeyError:
        return jsonify({'error': f"User with _id '{data['_id']}' already exists."}), 409
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500

@users_api.route('/<id>')
@token_required
def get_user(current_user,id):
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    result = list(USERS_COLLECTION.find({"_id": id}))
    if not result:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(result)

@users_api.route('/<id>/inventory', methods=['GET'])
@token_required
def get_user_inventory(current_user, id):
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    # looking inventory by 'id'
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # returning inventory
    return jsonify(user['inventory']), 200


@users_api.route('/<id>/inventory', methods=['POST', 'PUT'])
@token_required
def add_items_to_inventory(current_user,id):
    data = request.json
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'parts' not in data and 'sets' not in data:
        return jsonify({'error': 'Either "parts" and "sets" are required in the input.'}), 400

    if 'parts' in data:
        if not isinstance(data['parts'], list):
            return jsonify({'error': "'parts' must be a list of (_id, color, quantity) objects."}), 400
        for object_ in data['parts']:
            if not isinstance(object_, dict) or not all(key in object_ for key in ["_id", "color", "quantity"]):
                return jsonify({'error': f"Part should be a (_id, color, quantity) object."}), 400
            if not isinstance(object_["quantity"], int):
                return jsonify({'error': f"Invalid quantity for part {object_["_id"]}, color {object_["color"]}. Must be an integer."}), 400

    if 'sets' in data:
        if not isinstance(data['sets'], list):
            return jsonify({'error': "'sets' must be a list of (_id, quantity) objects."}), 400
        for object_ in data['sets']:
            if not isinstance(object_, dict) or ["_id", "quantity"] not in object_:
                return jsonify({'error': f"Set should be a (_id, quantity) object."}), 400
            if not isinstance(object_["quantity"], int):
                return jsonify({'error': f"Invalid quantity for set {object_["_id"]}. Must be an integer."}), 400

    for part_obj in data.get('parts', []):
        added = False
        for existing_part in user['inventory']['parts']:
            if existing_part['_id'] == part_obj['_id'] and existing_part['color'] == part_obj['color']:
                existing_part['quantity'] += part_obj['quantity']
                added = True
                break
        if not added:
            user['inventory']['parts'].append(part_obj)

    for set_obj in data.get('sets', []):
        added = False
        for existing_set in user['inventory']['sets']:
            if existing_set['_id'] == set_obj['_id']:
                existing_set['quantity'] += set_obj['quantity']
                added = True
                break
        if not added:
            user['inventory']['parts'].append(part_obj)

    result = USERS_COLLECTION.update_one({"_id": id}, {"$set": user})

    if result.matched_count == 0:
        return jsonify({'error': 'Operation failed'}), 400

    return jsonify(user['inventory'])

@users_api.route('/<id>/inventory', methods=['DELETE'])
@token_required
def remove_items_from_inventory(current_user,id):
    data = request.json
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
    
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    if 'parts' not in data and 'sets' not in data:
        return jsonify({'error': 'Either "parts" and "sets" are required in the input.'}), 400

    if 'parts' in data and not isinstance(data['parts'], list):
        return jsonify({'error': "'parts' must be a list of (_id, color) objects."}), 400

    if 'sets' in data and not isinstance(data['sets'], list):
        return jsonify({'error': "'sets' must be a list of _id."}), 400

    
    for part_id, quantity in data.get('parts', {}).items():
        if part_id not in user['inventory']['parts']:
            return jsonify({'error': f"Part with ID '{part_id}' not found in user's inventory."}), 404
        user['inventory']['parts'][part_id] -= quantity
        if user['inventory']['parts'][part_id] <= 0:
            del user['inventory']['parts'][part_id]

    removed_parts = 0
    for part_obj in data.get('parts', []):
        for existing_part in user['inventory']['parts']:
            if existing_part['_id'] == part_obj['_id'] and existing_part['color'] == part_obj['color']:
                del existing_part
                removed_parts += 1
                break

    removed_sets = 0
    for set_obj in data.get('sets', []):
        for existing_set in user['inventory']['sets']:
            if existing_set['_id'] == set_obj['_id']:
                del existing_set
                removed_sets += 1
                break

    USERS_COLLECTION.update_one({"_id": id}, {"$set": user})
    return jsonify(
        {
            "removed_parts" : removed_parts,
            "removed_sets": removed_sets
        }), 200


#  the rest of the crud operations for users
@users_api.route('/<id>', methods=['PUT'])
@token_required
def update_user(current_user,id):
    data = request.json
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
    
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400
    
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    update_fields = {}
    
    if 'password' in data:
        if not isinstance(data['password'], str):
            return jsonify({'error': 'Invalid password format. Must be a string.'}), 400
        update_fields['password'] = data['password']
    
    if 'is_admin' in data:
        if not isinstance(data['is_admin'], bool):
            return jsonify({'error': 'Invalid is_admin format. Must be a boolean.'}), 400
        update_fields['is_admin'] = data['is_admin']

    update_fields["inventory"] = user.get("inventory", {"sets": {}, "parts": {}})
    
    if update_fields:
        result = USERS_COLLECTION.update_one({"_id": id}, {"$set": update_fields})
        if result.matched_count == 0:
            return jsonify({'error': 'Update failed'}), 400
        return jsonify({'message': 'User updated successfully'}), 200
    else:
        return jsonify({'error': 'No valid fields to update'}), 400


# Delete User (DELETE /users/<id>)
@users_api.route('/<id>', methods=['DELETE'])
@token_required
def delete_user(current_user,id):
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    USERS_COLLECTION.delete_one({"_id": id})
    return jsonify({'message': f'User {id} deleted successfully'}), 200


#  most expensive owned part (include parts contained in sets)
@users_api.route('/<id>/inventory/most_expensive_part')
@token_required
def most_expensive_part(current_user, id):
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
      
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    most_expensive_part_ = None
    max_price = 0

    if 'inventory' in user and 'parts' in user['inventory']:
        for part_obj in user['inventory']['parts']:
            # Find the part in PARTS_COLLECTION
            part_id = part_obj['_id']
            color = part_obj['color']
            part = PARTS_COLLECTION.find_one({"_id": part_id})
            if part and part["colors"][color][0]["price"] > max_price:
                max_price = part["colors"][color][0]["price"]
                most_expensive_part_ = {
                    "_id":part_id,
                    "color": color
                }

    if most_expensive_part_:
        return jsonify({'most_expensive_part': most_expensive_part_, 'price': max_price}), 200
    else:
        return jsonify({'error': 'No parts found in inventory.'}), 404

@users_api.route('/<id>/inventory/total_value')
@token_required
def total_value_of_owned_parts(current_user, id):
    user = USERS_COLLECTION.find_one({"_id": id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
    
    total_value = 0.0
    
    inventory = user.get('inventory', {})
    parts = inventory.get('parts', [])
    
    for part_obj in parts:
        part_id = part_obj.get('_id')
        color = part_obj.get('color')
        quantity = part_obj.get('quantity', 0)
        
        if not part_id or not color or quantity <= 0:
            continue 
        
        part = PARTS_COLLECTION.find_one({"_id": part_id})
        
        if part and "colors" in part and color in part["colors"]:
            prices = [entry.get("Price", 0) for entry in part["colors"][color] if isinstance(entry, dict) and "Price" in entry]
            
            if prices:
                min_price = min(prices)  
                total_value += min_price * quantity
    
    return jsonify({'total_value': round(total_value, 2)})

    # Return the total value of owned parts
    return jsonify({'total_value': round(total_value, 2)})


@users_api.route('/<id>/inventory/completed/<top_count>', methods=['GET'])
# @token_required
def get_completed_percentage(id, top_count, current_user=None):
    top_count = int(top_count)
    # # chacking that curent user is the same as the user requested
    # if current_user['_id'] != id and not current_user.get('is_admin', False):
    #     return jsonify({'message': 'Unauthorized access'}), 403

    user = USERS_COLLECTION.find_one({"_id": id})

    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    user_inventory = user['inventory']
    result = []

    for set_obj in user_inventory['sets']:
        set_id = set_obj['_id']
        pipeline = [
            {
                '$match': {
                    '_id': set_id
                }
            }, {
                '$unwind': '$sim_scores'
            }, {
                '$project': {
                    '_id': 0, 
                    'similar_id': '$sim_scores._id', 
                    'score': '$sim_scores.similarity'
                }
            }, {
                '$sort': {
                    'score': -1
                }
            }, {
                '$limit': max(top_count, 10)
            }
        ]
        
        result.extend(list(SET_SIMILARITIES_COLLECTION.aggregate(pipeline)))
    result = list(sorted(result, key=lambda x: x['score'], reverse=True))
    result = result[:min(len(result), top_count)]
    final_result = []
    in_final = set()

    while len(final_result) < top_count and result:
        current = result.pop(0)
        if current['similar_id'] not in in_final:
            final_result.append(current)
            in_final.add(current['similar_id'])

    user_parts = _get_all_parts(id)
    final_percentage = []

    for final_set in final_result:
        set_contents = SET_CONTENTS_COLLECTION.find_one({"_id": final_set['similar_id']})
        common_parts = 0
        total_parts = set_contents['num_parts']
        set_parts = set_contents['parts']

        for part_obj in set_parts:
            part_id = part_obj['_id']
            colors = part_obj['colors']
            for color_obj in colors:
                color = color_obj['color']
                quantity = color_obj['quantity']
                if (part_id, color) in user_parts:
                    common_parts += min(quantity, user_parts[(part_id, color)])
        final_percentage.append({'set_id': final_set['similar_id'], 'percentage': round(common_parts / total_parts * 100, 2)})

    return jsonify(final_percentage)     

def _get_all_parts(uid):
    user = USERS_COLLECTION.find_one({"_id": uid})
    if user is None:
        raise KeyError(uid)
    
    all_parts = {}
    for elem in user['inventory']['parts']:
        all_parts[(elem['_id'], elem['color'])] = elem['quantity']

    for brickset in user['inventory']['sets']:
        brickset_id = brickset["_id"]
        for part_obj in SET_CONTENTS_COLLECTION.find_one({"_id": brickset_id})["parts"]:
            part_id = part_obj["_id"]
            colors = part_obj["colors"]
            for color_obj in colors:
                color, quantity = color_obj["color"], color_obj["quantity"]
                if (part_id, color) in all_parts:
                    all_parts[(part_id, color)] += quantity
                else:
                    all_parts[(part_id, color)] = quantity

    return all_parts

@users_api.route('/<id>/inventory/cheapest_set', methods=['GET'])
@token_required
def find_cheapest_from_inventory(current_user, id):
    # Ensure the user is authorized to access this data
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    # Fetch user's inventory (parts they own)
    user_parts = _get_all_parts(id)

    # Retrieve all sets and only necessary fields (_id and parts)
    all_sets = list(SET_CONTENTS_COLLECTION.find({}, {"_id": 1, "parts": 1}))

    # Retrieve all set overviews in a single query (store them in a dictionary for fast lookup)
    set_overviews = {
        doc["_id"]: doc for doc in SET_OVERVIEWS_COLLECTION.find(
            {}, {"_id": 1, "name": 1, "year": 1, "num_parts": 1, "min_offer": 1}
        )
    }

    possible_sets = []

    # Loop through each set
    for set_doc in all_sets:
        set_id = set_doc["_id"]
        set_parts = set_doc["parts"]

        # Skip sets that do not have an overview (no price data)
        if set_id not in set_overviews:
            continue  

        set_overview = set_overviews[set_id]

        total_parts_in_set = 0
        owned_parts_count = 0

        # Handle both list-based and dictionary-based part formats
        if isinstance(set_parts, list):
            for part in set_parts:
                part_id = part["_id"]
                for color_info in part.get('colors', []):
                    color = color_info['color']
                    quantity = color_info['quantity']
                    user_quantity = user_parts.get((part_id, color), 0)
                    total_parts_in_set += quantity
                    owned_parts_count += min(user_quantity, quantity)
        else:
            for part_id, part_info in set_parts.items():
                total_parts_in_set += part_info["quantity"]
                user_quantity = user_parts.get((part_id, part_info["color"]), 0)
                owned_parts_count += min(user_quantity, part_info["quantity"])

        # Skip sets that are already fully completed
        if owned_parts_count >= total_parts_in_set:
            continue

        # Add set to the list of potential options
        possible_sets.append({
            "set_id": set_id,
            "name": set_overview["name"],
            "year": set_overview["year"],
            "num_parts": set_overview["num_parts"],
            "min_offer": set_overview.get("min_offer", float('inf'))  # Default to infinity if no price is found
        })

    # Sort sets by price and select the top 10 cheapest
    cheapest_sets = sorted(possible_sets, key=lambda x: x["min_offer"])[:10]

    # If no sets found, return a 404 response
    if not cheapest_sets:
        return jsonify({"message": "No sets found"}), 404

    # Return the top 10 cheapest sets
    return jsonify({"cheapest_sets": cheapest_sets})
