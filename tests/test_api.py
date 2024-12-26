import pytest
from back_serv import flask_app
import json

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_submit_task(client):
    """Test task submission endpoint"""
    response = client.post('/submit_task', 
                         data=json.dumps({
                             'task_type': 'image_creation',
                             'task_params': {'prompt': 'test'},
                             'user_id': 'test_user'
                         }),
                         content_type='application/json')
    assert response.status_code == 202
    data = json.loads(response.data)
    assert 'ticket_id' in data
    assert 'status' in data
    assert data['status'] == 'Queueing'

def test_query_task(client):
    """Test task query endpoint"""
    # First submit a task
    response = client.post('/submit_task',
                         data=json.dumps({
                             'task_type': 'image_creation',
                             'task_params': {'prompt': 'test'},
                             'user_id': 'test_user'
                         }),
                         content_type='application/json')
    ticket_id = json.loads(response.data)['ticket_id']
    
    # Then query it
    response = client.get(f'/query_task/{ticket_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data

def test_cancel_task(client):
    """Test task cancellation endpoint"""
    # First submit a task
    response = client.post('/submit_task',
                         data=json.dumps({
                             'task_type': 'image_creation',
                             'task_params': {'prompt': 'test'},
                             'user_id': 'test_user'
                         }),
                         content_type='application/json')
    ticket_id = json.loads(response.data)['ticket_id']
    
    # Then cancel it
    response = client.post(f'/cancel_task/{ticket_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'Cancelled'

def test_invalid_task_type(client):
    """Test submitting task with invalid task type"""
    response = client.post('/submit_task',
                         data=json.dumps({
                             'task_type': 'invalid_type',
                             'task_params': {},
                             'user_id': 'test_user'
                         }),
                         content_type='application/json')
    assert response.status_code == 400

def test_missing_parameters(client):
    """Test submitting task with missing parameters"""
    response = client.post('/submit_task',
                         data=json.dumps({
                             'task_type': 'image_creation',
                             'user_id': 'test_user'
                         }),
                         content_type='application/json')
    assert response.status_code == 400
