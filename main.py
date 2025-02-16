import os
from flask import Flask, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from user import users_api
from parts import parts_api
from colors import colors_api
from sets import sets_api
from stats import stats_api
from imports import *

# === APP CONFIGURATION ===
app = Flask(__name__)
app.config['SECRET_KEY'] = "your_secret_key"
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "*"}})


# === REGISTER BLUEPRINTS ===
app.register_blueprint(users_api, url_prefix='/users') 
app.register_blueprint(parts_api, url_prefix='/parts')
app.register_blueprint(colors_api, url_prefix='/colors')
app.register_blueprint(sets_api, url_prefix='/sets')
app.register_blueprint(stats_api, url_prefix='/stats')
app.config['SECRET_KEY'] = "your_secret_key"

# === ROOT ROUTE ===
@app.route('/')
def index():
    return "Welcome to Brickscrapper API"

# === SWAGGER CONFIGURATION ===
SWAGGER_URL = '/swagger'  # URL for accessing Swagger UI
API_URL = '/swagger.json'  # Endpoint for Swagger JSON

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, 
    API_URL,
    config={
        'app_name': "Unipi Databases API"
    }
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

# === SWAGGER.JSON ENDPOINT ===
@app.route("/swagger.json")
def swagger_json():
    try:
        return send_from_directory(
            directory=os.path.join(app.root_path, 'static'),
            path='swagger.json',
            mimetype='application/json'
        )
    except FileNotFoundError:
        return {"error": "swagger.json file not found in /static folder"}, 404

# === MAIN ENTRY POINT ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)