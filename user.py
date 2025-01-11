from unittest import result
from flask import Blueprint
from imports import *

users_api = Blueprint('users_api', __name__)
USERS_COLLECTION = DB['users']
PARTS_COLLECTION = DB['parts']
SETS_COLLECTION = DB['sets']
COLORS_COLLECTION = DB['colors']

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

    # Walidacja wejściowych danych
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400

    # Walidacja danych części
    if 'parts' in data:
        if not isinstance(data['parts'], dict):
            return jsonify({'error': "'parts' must be a dictionary with part IDs as keys and colors with quantities as values."}), 400
        for part_id, colors in data['parts'].items():
            if not isinstance(colors, dict):
                return jsonify({'error': f"Part {part_id} colors should be a dictionary."}), 400
            for color, quantity in colors.items():
                if not isinstance(quantity, int):
                    return jsonify({'error': f"Invalid quantity for part {part_id}, color {color}. Must be an integer."}), 400

    # Walidacja danych zestawów
    if 'sets' in data:
        if not isinstance(data['sets'], dict):
            return jsonify({'error': "'sets' must be a dictionary with set IDs as keys and quantities as values."}), 400
        for set_id, quantity in data['sets'].items():
            if not isinstance(quantity, int):
                return jsonify({'error': f"Invalid quantity for set {set_id}. Must be an integer."}), 400

    # Pobranie użytkownika z bazy
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Dodawanie części do inwentarza
    for part_id, colors in data.get('parts', {}).items():
        if part_id not in user['inventory']['parts']:
            user['inventory']['parts'][part_id] = {}
        for color, quantity in colors.items():
            if color not in user['inventory']['parts'][part_id]:
                user['inventory']['parts'][part_id][color] = 0
            user['inventory']['parts'][part_id][color] += quantity

    # Dodawanie zestawów do inwentarza
    for set_id, quantity in data.get('sets', {}).items():
        if set_id not in user['inventory']['sets']:
            user['inventory']['sets'][set_id] = 0
        user['inventory']['sets'][set_id] += quantity

    # Zaktualizowanie użytkownika w bazie
    result = USERS_COLLECTION.update_one({"_id": id}, {"$set": user})

    if result.matched_count == 0:
        return jsonify({'error': 'Operation failed'}), 400

    # Zwrócenie nowego inwentarza
    return jsonify(user['inventory'])

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

# TODO the rest of the crud operations for users
# Update User (PUT /users/<id>)
@users_api.route('/<id>', methods=['PUT'])
def update_user(id):
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input. JSON body is required.'}), 400
    
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    update_fields = {}
    if 'password' in data:
        update_fields['password'] = data['password']
    if 'is_admin' in data:
        update_fields['is_admin'] = data['is_admin']
    
    if update_fields:
        result = USERS_COLLECTION.update_one({"_id": id}, {"$set": update_fields})
        if result.matched_count == 0:
            return jsonify({'error': 'Update failed'}), 400
        return jsonify({'message': 'User updated successfully'}), 200
    else:
        return jsonify({'error': 'No valid fields to update'}), 400

# Delete User (DELETE /users/<id>)
@users_api.route('/<id>', methods=['DELETE'])
def delete_user(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    USERS_COLLECTION.delete_one({"_id": id})
    return jsonify({'message': f'User {id} deleted successfully'}), 200


# TODO most expensive owned part (include parts contained in sets)
@users_api.route('/<id>/inventory/most_expensive_part')
def most_expensive_part(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Przechodzimy przez część użytkownika w inwentarzu (jeśli istnieje w parts)
    most_expensive_part = None
    max_price = 0

    # Sprawdzamy części w inwentarzu użytkownika
    if 'inventory' in user and 'parts' in user['inventory']:
        for part_id, colors in user['inventory']['parts'].items():
            # Znajdź część w PARTS_COLLECTION
            part = PARTS_COLLECTION.find_one({"_id": part_id})
            if part:
                # Część istnieje, sprawdzamy ceny jej kolorów
                for color, quantity in colors.items():
                    # Sprawdzamy, czy są kolory i ceny w tej części
                    if 'colors' in part and isinstance(part['colors'], dict):
                        color_entries = part['colors'].get(color, [])
                        for entry in color_entries:
                            if isinstance(entry, dict) and 'Price' in entry:
                                price = entry['Price']  # Cena tego koloru
                                total_price = price * quantity  # Całkowita cena = cena * ilość
                                if total_price > max_price:
                                    max_price = total_price
                                    most_expensive_part = part_id

    # Zwracamy najdroższą część w inwentarzu użytkownika
    if most_expensive_part:
        return jsonify({'most_expensive_part': most_expensive_part, 'price': max_price})
    else:
        return jsonify({'error': 'No parts found in inventory.'}), 404


# TODO cheapest unowned sets to complete given inventory
@users_api.route('/<id>/inventory/cheapest_set_to_complete', methods=['GET'])
def cheapest_set_to_complete(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_inventory = user.get('inventory', {}).get('parts', {})

    color_map = {color['_id']: color['name'] for color in COLORS_COLLECTION.find()}

    user_part_ids = list(user_inventory.keys())
    relevant_sets = SETS_COLLECTION.find({
        "$or": [
            {f"parts.{part_id}": {"$exists": True}} for part_id in user_part_ids
        ]
    })

    result = []

    for set_data in relevant_sets:
        set_id = set_data['_id']
        set_name = set_data['name']
        set_parts = set_data['parts']
        
        total_min_cost = 0
        owned_parts = 0
        total_parts = set_data.get('num_parts', 0)

        missing_parts_info = []  

        for part_id, part_data in set_parts.items():
            required_quantity = part_data['quantity']
            color_id = part_data['color']
            color_name = color_map.get(color_id)

            if not color_name:
                continue  

            # Liczba części w inwentarzu użytkownika
            user_quantity = user_inventory.get(part_id, {}).get(color_name, 0)
            owned_quantity = min(user_quantity, required_quantity)
            missing_quantity = max(0, required_quantity - owned_quantity)
            owned_parts += owned_quantity

            if missing_quantity > 0:
                # Pobranie ceny brakujących części
                part_info = PARTS_COLLECTION.find_one({"_id": part_id})
                if not part_info:
                    missing_parts_info.append({
                        "part_id": part_id,
                        "color_name": color_name,
                        "reason": "Part not found in PARTS_COLLECTION"
                    })
                    continue

                # Pobranie listy cen dla danego koloru
                color_data = part_info.get('colors', {}).get(color_name, [])
                if not color_data:
                    missing_parts_info.append({
                        "part_id": part_id,
                        "color_name": color_name,
                        "reason": "No price data available for this color"
                    })
                    continue

                # Najniższa cena
                min_price = min(entry['Price'] for entry in color_data)
                total_min_cost += missing_quantity * min_price

    
        result.append({
            "set_id": set_id,
            "name": set_name,
            "total_min_cost": total_min_cost,
            "owned_parts": owned_parts,
            "missing_parts_info": missing_parts_info 
        })

    # Sortowanie wyników po koszcie zestawu
    result = sorted(result, key=lambda x: x['total_min_cost'])

    # Finalny wynik
    return jsonify(result)


# TODO total value of owned parts
@users_api.route('/<id>/inventory/total_value')
def total_value_of_owned_parts(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    total_value = 0
    # Sprawdzamy części w inwentarzu użytkownika
    if 'inventory' in user and 'parts' in user['inventory']:
        for part_id, colors in user['inventory']['parts'].items():
            # Znajdź część w PARTS_COLLECTION
            part = PARTS_COLLECTION.find_one({"_id": part_id})
            if part:
                # Część istnieje, sprawdzamy ceny jej kolorów
                for color, quantity in colors.items():
                    # Sprawdzamy, czy są kolory i ceny w tej części
                    if 'colors' in part and isinstance(part['colors'], dict):
                        color_entries = part['colors'].get(color, [])
                        
                        # Jeśli mamy ceny dla tego koloru, znajdź najwyższą cenę
                        if color_entries:
                            max_price = 0
                            for entry in color_entries:
                                if isinstance(entry, dict) and 'Price' in entry:
                                    price = entry['Price']
                                    if price > max_price:
                                        max_price = price  # Wybieramy najwyższą cenę dla tego koloru

                            if max_price > 0:  # Jeśli mamy cenę dla tego koloru
                                total_price = max_price * quantity  # Całkowita cena = cena * ilość
                                total_value += total_price  # Sumujemy wartości wszystkich części

    # Zwracamy łączną wartość posiadanych części
    return jsonify({'total_value': round(total_value, 2)})

# TODO percent of set completion given inventory
@users_api.route('/<id>/inventory/set_completed_percentage', methods=['GET'])
def set_completed_percentage(id):
    user = USERS_COLLECTION.find_one({"_id": id})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_inventory = user.get('inventory', {}).get('parts', {})
    
    # Mapowanie kolorów
    color_map = {color['_id']: color['name'] for color in COLORS_COLLECTION.find()}

    # Tylko zestawy, które zawierają części użytkownika
    user_part_ids = list(user_inventory.keys())
    relevant_sets = SETS_COLLECTION.find({
        "$or": [
            {f"parts.{part_id}": {"$exists": True}} for part_id in user_part_ids
        ]
    })

    result = []
    for set_data in relevant_sets:
        set_id = set_data['_id']
        set_name = set_data['name']
        total_parts = set_data.get('num_parts', 0)  # Pobieramy total_parts z num_parts
        set_parts = set_data['parts']

        owned_parts = 0

        # Porównanie części zestawu z inwentarzem użytkownika
        for part_id, part_data in set_parts.items():
            required_quantity = part_data['quantity']
            color_id = part_data['color']
            color_name = color_map.get(color_id)

            if not color_name:
                continue  # Jeśli kolor nie istnieje w mapie, pomijamy tę część

            # Sprawdzamy, ile użytkownik ma tej części w danym kolorze
            user_quantity = user_inventory.get(part_id, {}).get(color_name, 0)
            owned_parts += min(user_quantity, required_quantity)

        # Obliczamy procent posiadanych części
        completion_percentage = (owned_parts / total_parts) * 100 if total_parts > 0 else 0

        result.append({
            "set_id": set_id,
            "name": set_name,
            "completion_percentage": completion_percentage,
            "total_parts": total_parts,
            "owned_parts": owned_parts
        })

    # Sortujemy wyniki po procentach posiadanych części
    result = sorted(result, key=lambda x: x['completion_percentage'], reverse=True)

    return jsonify(result)
