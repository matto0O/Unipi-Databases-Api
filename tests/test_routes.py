import pytest
from flask import Flask
from mongomock import Database, MongoClient
from stats import stats_api, get_set_statistics, get_part_statistics, get_user_statistics
from parts import parts_api, get_parts
from sets import sets_api, get_set, get_profitable_sets,get_cheapest_new_sets, get_cheapest_used_sets
from user import users_api, get_users,get_user_inventory,most_expensive_part, total_value_of_owned_parts,set_completed_percentage,find_cheapest_from_inventory

@pytest.fixture
def mock_db():
    client = MongoClient()
    db = client['test_db']  
    return db
  


@pytest.fixture
def app(mock_db, monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(stats_api, url_prefix='/stats')
    app.register_blueprint(sets_api, url_prefix='/sets')
    app.register_blueprint(parts_api, url_prefix='/parts')
    app.register_blueprint(users_api, url_prefix='/users')

    monkeypatch.setattr('stats.DB', mock_db)
    monkeypatch.setattr('parts.DB', mock_db)
    monkeypatch.setattr('sets.DB', mock_db)
    monkeypatch.setattr('user.DB', mock_db)

    return app

def test_get_set_statistics(client):
    response = client.get('/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'sets' in data
    assert data['sets']['total_sets'] == 4468

def test_get_part_statistics(client):
    response = client.get('/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'parts' in data
    assert data['parts']['total_parts'] == 4392

def test_get_user_statistics(client):
    response = client.get('/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'users' in data

def test_get_part(client):
    response = client.get('/parts/92911')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'colors' in data[0]

def test_get_sets(client):
    response = client.get('/sets')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'name' in data[0]
    assert 'year' in data[0]
    assert 'num_parts' in data[0]

def test_get_profitable_sets(client):
    response = client.get('/sets/profitable/3')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'name' in data[0]
    assert 'year' in data[0]
    assert 'num_parts' in data[0]

def test_get_cheapest_new_sets(client):
    response = client.get('/sets/cheapest/new/3')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_cheapest_used_sets(client):
    response = client.get('/sets/cheapest/used/3')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

# Test cases for user.py
def test_get_users(client):
    response = client.get('/users')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert '_id' in data[0]
    assert 'inventory' in data[0]


def test_get_user_inventory(client):
    response = client.get('/users/admin/inventory')
    assert response.status_code == 200
    data = response.get_json()

def test_most_expensive_part(client):
    response = client.get('users/test/inventory/most_expensive_part')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'most_expensive_part' in data


def test_total_value_of_owned_parts(client):
    response = client.get('users/admin/inventory/total_value')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'total_value' in data


def test_set_completed_percentage(client):
    response = client.get('users/admin/inventory/completed/5')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    for item in data:
        assert 'percentage' in item
        assert 'set_id' in item
        assert isinstance(item['percentage'], (int, float))
        assert isinstance(item['set_id'], str)


def test_find_cheapest_from_inventory(client):
    response = client.get('/users/user1/inventory/cheapest_set')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'cheapest_set' in data
    assert 'completed_percentages' in data
    assert isinstance(data['cheapest_set'], dict)
    assert isinstance(data['completed_percentages'], list)
    assert 'completion_percentage' in data['cheapest_set']
    assert 'min_offer' in data['cheapest_set']
    assert 'name' in data['cheapest_set']
    assert 'num_parts' in data['cheapest_set']
    assert 'set_id' in data['cheapest_set']
    assert 'year' in data['cheapest_set']
    for item in data['completed_percentages']:
        assert 'completion_percentage' in item
        assert 'set_id' in item













