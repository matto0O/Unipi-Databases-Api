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
    return jsonify(result), 200

@colors_api.route('/<id>')
@redis_cache(module='colors')
def get_color(id):
    result = list(COLORS_COLLECTION.find({"_id": int(id)}))
    if not result:
        return jsonify({'error': 'Color not found'}), 404
    return jsonify(result) 

# TODO add new color (include id in request)

# TODO delete a color