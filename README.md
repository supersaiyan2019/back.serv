# Back.Serv

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Celery](https://img.shields.io/badge/celery-5.0+-green.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

Back.Serv is a distributed AI task processing system built with Flask and Celery. It provides a robust and scalable backend service for managing and executing various AI-related tasks across multiple servers.

## Features

- **Distributed Task Processing**: Efficiently manage and distribute AI tasks across multiple servers
- **Smart Load Balancing**: Automatically select the least loaded server for task execution
- **Fault Tolerance**: Automatic task rescheduling and server failover mechanisms
- **Real-time Monitoring**: Track task status and server health in real-time
- **REST API Interface**: Simple and intuitive API endpoints for task submission and management

## Supported AI Tasks

- Image Creation
- Image Upscaling
- Face Swap
- Video Creation
- Translation Services
- Prompt Services
- Face Detection

## System Architecture

The system consists of several key components:

- **Flask Backend**: Handles HTTP requests and task management
- **Celery Workers**: Processes distributed tasks asynchronously
- **Redis**: Message broker for task queue management
- **MySQL**: Persistent storage for task information and system state
- **Health Monitoring**: Continuous monitoring of server status and task progress

## Quick Start

### Prerequisites

- Python 3.8+
- Redis Server
- MySQL Server
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/back.serv.git
cd back.serv
```

2. Create and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your database settings in `.env`

5. Start the Redis server:
```bash
redis-server
```

6. Start the Celery worker:
```bash
celery -A celery_tasks worker --loglevel=info
```

7. Run the Flask application:
```bash
python back_serv.py
```

## Testing

The project includes comprehensive test coverage for both API endpoints and Celery tasks.

### Running Tests

1. Install test dependencies:
```bash
pip install pytest pytest-cov
```

2. Run the test suite:
```bash
pytest
```

3. View test coverage report:
```bash
pytest --cov=. --cov-report=html
```

The HTML coverage report will be available in the `htmlcov` directory.

### Test Structure

- `tests/test_api.py`: API endpoint tests
- `tests/test_celery_tasks.py`: Celery task tests

## API Documentation

### Submit Task
```http
POST /submit_task
Content-Type: application/json

{
    "task_type": "image_creation",
    "task_params": {},
    "user_id": "user123"
}
```

### Query Task Status
```http
GET /query_task/<ticket_id>
```

### Cancel Task
```http
POST /cancel_task/<ticket_id>
```

## Configuration

The system can be configured through environment variables or configuration files. Key configuration options include:

- Database connection settings
- Redis connection settings
- Server health check intervals
- Task timeout thresholds

For detailed configuration options, see the [Configuration Guide](docs/configuration.md).

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please:
1. Check the [documentation](docs/)
2. Search through [existing issues](https://github.com/yourusername/back.serv/issues)
3. Create a new issue if needed

## Acknowledgments

- Thanks to all contributors who have helped shape Back.Serv
- Built with Flask, Celery, and other amazing open source projects
