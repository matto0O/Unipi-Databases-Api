import flask
from dotenv import load_dotenv
import os
from pymongo import MongoClient

app = flask.Flask(__name__)
load_dotenv()
CLIENT = MongoClient(os.getenv('MONGO_URI'))
DB = CLIENT['bricks']
SETS_COLLECTION = DB['sets']

@app.route('/')
def index():
    return str(SETS_COLLECTION.count_documents({}))

@app.route('/sets/<id>')
def get_set(id):
    result = list(SETS_COLLECTION.find({"_id": str(id)}))
    return flask.jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
