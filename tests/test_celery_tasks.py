import pytest
from celery_tasks import app, process_task_queue
from unittest.mock import patch, MagicMock

@pytest.fixture
def celery_app(request):
    app.conf.update(CELERY_ALWAYS_EAGER=True)
    return app

def test_process_task_queue():
    """Test the task queue processing"""
    with patch('celery_tasks.get_db_connection') as mock_db:
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_db.return_value.cursor.return_value = mock_cursor
        
        # Mock task data
        mock_cursor.fetchall.return_value = [{
            'ticket_id': 'test_ticket',
            'task_type': 'image_creation',
            'task_params': '{"prompt": "test"}',
            'user_id': 'test_user',
            'serv_name': 'test_server'
        }]
        
        # Run the task
        result = process_task_queue.delay()
        assert result.successful()

@pytest.mark.parametrize("task_type,task_params", [
    ('image_creation', {'prompt': 'test'}),
    ('image_upscale', {'image_url': 'test.jpg', 'scale_factor': 2}),
    ('face_swap', {'source_image': 'source.jpg', 'target_image': 'target.jpg'}),
    ('video_creation', {'prompt': 'test', 'duration': 10})
])
def test_task_types(celery_app, task_type, task_params):
    """Test different task types"""
    with patch('celery_tasks.get_db_connection') as mock_db:
        # Mock database connection
        mock_cursor = MagicMock()
        mock_db.return_value.cursor.return_value = mock_cursor
        
        # Create task
        task = celery_app.send_task(task_type, 
                                  args=[task_params, 'test_user', 'test_server'])
        assert task.status == 'SUCCESS'

def test_task_failure_handling():
    """Test handling of task failures"""
    with patch('celery_tasks.get_db_connection') as mock_db:
        mock_cursor = MagicMock()
        mock_db.return_value.cursor.return_value = mock_cursor
        
        # Mock a failing task
        mock_cursor.fetchall.return_value = [{
            'ticket_id': 'test_ticket',
            'task_type': 'invalid_task',
            'task_params': '{}',
            'user_id': 'test_user',
            'serv_name': 'test_server'
        }]
        
        # Run the task
        result = process_task_queue.delay()
        assert result.successful()
        
        # Verify error status was updated
        mock_cursor.execute.assert_called()

def test_server_selection():
    """Test server selection logic"""
    with patch('celery_tasks.get_server_load') as mock_load:
        mock_load.return_value = {
            'server1': {'active_tasks': 5, 'stuck_tasks': 1},
            'server2': {'active_tasks': 2, 'stuck_tasks': 0},
            'server3': {'active_tasks': 8, 'stuck_tasks': 2}
        }
        
        # Server2 should be selected as it has the lowest load
        selected_server = app.get_available_server()
        assert selected_server == 'server2'
