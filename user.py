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
SET_SIMILARITIES_COLLECTION = DB['set_similarities']
SET_OFFERS_COLLECTION = DB['set_offers']
COLORS_COLLECTION = DB['colors']

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


@users_api.route('/<id>/inventory', methods=['POST'])
@token_required
def add_items_to_inventory(current_user,id):
    data = request.json
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    if 'parts' not in data or 'sets' not in data:
        return jsonify({'error': 'Both "parts" and "sets" are required in the input.'}), 400

    if 'parts' in data:
        if not isinstance(data['parts'], dict):
            return jsonify({'error': "'parts' must be a dictionary with part IDs as keys and colors with quantities as values."}), 400
        for part_id, colors in data['parts'].items():
            if not isinstance(colors, dict):
                return jsonify({'error': f"Part {part_id} colors should be a dictionary."}), 400
            for color, quantity in colors.items():
                if not isinstance(quantity, int):
                    return jsonify({'error': f"Invalid quantity for part {part_id}, color {color}. Must be an integer."}), 400

    if 'sets' in data:
        if not isinstance(data['sets'], dict):
            return jsonify({'error': "'sets' must be a dictionary with set IDs as keys and quantities as values."}), 400
        for set_id, quantity in data['sets'].items():
            if not isinstance(quantity, int):
                return jsonify({'error': f"Invalid quantity for set {set_id}. Must be an integer."}), 400

    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    for part_id, colors in data.get('parts', {}).items():
        if part_id not in user['inventory']['parts']:
            user['inventory']['parts'][part_id] = {}
        for color, quantity in colors.items():
            if color not in user['inventory']['parts'][part_id]:
                user['inventory']['parts'][part_id][color] = 0
            user['inventory']['parts'][part_id][color] += quantity

    for set_id, quantity in data.get('sets', {}).items():
        if set_id not in user['inventory']['sets']:
            user['inventory']['sets'][set_id] = 0
        user['inventory']['sets'][set_id] += quantity

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
    
    if 'inventory' in data:
        if not isinstance(data['inventory'], dict):
            return jsonify({'error': 'Invalid inventory format. Must be an object.'}), 400
        
        inventory_updates = {}
        
        if 'parts' in data['inventory']:
            if not isinstance(data['inventory']['parts'], dict):
                return jsonify({'error': 'Invalid parts format. Must be an object.'}), 400
            
            for part_id, colors in data['inventory']['parts'].items():
                if not isinstance(colors, dict):
                    return jsonify({'error': f'Invalid format for part {part_id}. Must be an object.'}), 400
                
                for color, quantity in colors.items():
                    if not isinstance(quantity, int):
                        return jsonify({'error': f'Invalid quantity format for part {part_id}, color {color}. Must be an integer.'}), 400
            
            inventory_updates['parts'] = data['inventory']['parts']
        
        if 'sets' in data['inventory']:
            if not isinstance(data['inventory']['sets'], dict):
                return jsonify({'error': 'Invalid sets format. Must be an object.'}), 400
            
            for set_id, quantity in data['inventory']['sets'].items():
                if not isinstance(quantity, int):
                    return jsonify({'error': f'Invalid quantity format for set {set_id}. Must be an integer.'}), 400
            
            inventory_updates['sets'] = data['inventory']['sets']
        
        update_fields['inventory'] = inventory_updates
    
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

    most_expensive_part = None
    max_price = 0

    if 'inventory' in user and 'parts' in user['inventory']:
        for part_id, colors in user['inventory']['parts'].items():
            # Find the part in PARTS_COLLECTION
            part = PARTS_COLLECTION.find_one({"_id": part_id})
            if part:
                # Part exists, check the prices of its colors
                for color, quantity in colors.items():
                    # Check if there are colors and prices in this part
                    if 'colors' in part and isinstance(part['colors'], dict):
                        color_entries = part['colors'].get(color, [])
                        for entry in color_entries:
                            if isinstance(entry, dict) and 'Price' in entry:
                                price = entry['Price']  # Price of this color
                                total_price = price * quantity 
                                if total_price > max_price:
                                    max_price = total_price
                                    most_expensive_part = part_id

    if most_expensive_part:
        return jsonify({'most_expensive_part': most_expensive_part, 'price': max_price})
    else:
        return jsonify({'error': 'No parts found in inventory.'}), 404

@users_api.route('/<id>/inventory/total_value')
@token_required
def total_value_of_owned_parts(current_user,id):
    user = USERS_COLLECTION.find_one({"_id": id})
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    total_value = 0
    # Check parts in user's inventory
    if 'inventory' in user and 'parts' in user['inventory']:
        for part_id, colors in user['inventory']['parts'].items():
            # Find the part in PARTS_COLLECTION
            part = PARTS_COLLECTION.find_one({"_id": part_id})
            if part:
                # Part exists, check the prices of its colors
                for color, quantity in colors.items():
                    # Check if there are colors and prices in this part
                    if 'colors' in part and isinstance(part['colors'], dict):
                        color_entries = part['colors'].get(color, [])
                        
                        # If we have prices for this color, find the highest price
                        if color_entries:
                            max_price = 0
                            for entry in color_entries:
                                if isinstance(entry, dict) and 'Price' in entry:
                                    price = entry['Price']
                                    if price > max_price:
                                        max_price = price  # Choose the highest price for this color

                            if max_price > 0:  # If we have a price for this color
                                total_price = max_price * quantity  # Total price = price * quantity
                                total_value += total_price  # Sum the values of all parts

    # Return the total value of owned parts
    return jsonify({'total_value': round(total_value, 2)})

@users_api.route('/<id>/inventory/completed/<top_count>', methods=['GET'])
@token_required
def set_completed_percentage(id, top_count, current_user):
    top_count = int(top_count)
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403

    user = USERS_COLLECTION.find_one({"_id": id})

    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    user_inventory = user['inventory']
    result = []

    for set_id, _ in user_inventory['sets'].items():
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
                    'similar_id': {
                        '$arrayElemAt': [
                            '$sim_scores', 0
                        ]
                    }, 
                    'score': {
                        '$arrayElemAt': [
                            '$sim_scores', 1
                        ]
                    }
                }
            }, {
                '$sort': {
                    'score': -1
                }
            }, {
                '$limit': 10
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

        for part_id, val in set_parts.items():
            if (part_id, val['color']) in user_parts:
                common_parts += min(val['quantity'], user_parts[(part_id, val['color'])])
        final_percentage.append({'set_id': final_set['similar_id'], 'percentage': round(common_parts / total_parts * 100, 2)})

    return jsonify(final_percentage)     

def _get_all_parts(uid):
    user = USERS_COLLECTION.find_one({"_id": uid})
    if user is None:
        raise KeyError(uid)
    all_parts = {}
    for part_id, colors in user['inventory']['parts'].items():
        for color, quantity in colors.items():
            all_parts[(part_id, color)] = quantity

    for brickset in user['inventory']['sets']:
        for part_id, val in SET_CONTENTS_COLLECTION.find_one({"_id": brickset})["parts"].items():
            if (part_id, val["color"]) in all_parts:
                all_parts[(part_id, val["color"])] += val["quantity"]
            else:
                all_parts[(part_id, val["color"])] = val["quantity"]

    return all_parts

#This function compute the cheapest set that the user can complete
@users_api.route('/<id>/inventory/cheapest_set', methods=['GET'])
@token_required
def find_cheapest_from_inventory(current_user,id):
    # chacking that curent user is the same as the user requested
    if current_user['_id'] != id and not current_user.get('is_admin', False):
        return jsonify({'message': 'Unauthorized access'}), 403
  
    user_parts = _get_all_parts(id)
    completed_percentages = []

    all_sets = SET_CONTENTS_COLLECTION.find()

    for set_doc in all_sets:
        set_id = set_doc["_id"]
        set_parts = set_doc["parts"]
        total_parts_in_set = 0
        owned_parts_count = 0

        for part_id, part_info in set_parts.items():
            total_parts_in_set += part_info["quantity"]
            user_quantity = user_parts.get((part_id, part_info["color"]), 0)
            owned_parts_count += min(user_quantity, part_info["quantity"])

        if total_parts_in_set > 0:
            completion_percentage = (owned_parts_count / total_parts_in_set) * 100
        else:
            completion_percentage = 0

        if completion_percentage < 100:  # Skip sets with 100% completion
            completed_percentages.append({
                "set_id": set_id,
                "completion_percentage": round(completion_percentage, 2)
            })

    completed_percentages.sort(key=lambda x: x["completion_percentage"], reverse=True)
    completed_percentages = completed_percentages[:10]  # Only consider the top 10

    cheapest_set = None
    min_price = float('inf')

    for set_info in completed_percentages:
        set_id = set_info["set_id"]

        set_overview = SET_OVERVIEWS_COLLECTION.find_one({"_id": set_id})
        if set_overview and "min_offer" in set_overview:
            if set_overview["min_offer"] < min_price:
                min_offer = set_overview["min_offer"]
                cheapest_set = {
                    "set_id": set_id,
                    "name": set_overview["name"],
                    "year": set_overview["year"],
                    "num_parts": set_overview["num_parts"],
                    "min_offer": set_overview["min_offer"],
                    "completion_percentage": set_info["completion_percentage"]
                }

    if not cheapest_set:
        return jsonify({
            "completed_percentages": completed_percentages
        }), 404

    return jsonify({
        "cheapest_set": cheapest_set,
        "completed_percentages": completed_percentages
    })
