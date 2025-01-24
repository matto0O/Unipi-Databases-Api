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
SETS_COLLECTION = DB['sets']

@app.route('/')
def index():
    return str(SETS_COLLECTION.count_documents({}))

if __name__ == '__main__':
    app.run(debug=True)
