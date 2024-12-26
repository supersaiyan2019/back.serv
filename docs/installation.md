# Installation Guide

This guide will help you set up Back.Serv on your system.

## Prerequisites

Before installing Back.Serv, ensure you have the following:

- Python 3.8 or higher
- Redis server
- MySQL server
- Git (for cloning the repository)

## Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/back.serv.git
   cd back.serv
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` file with your configuration settings.

5. **Initialize Database**
   Create the necessary database and tables using the provided SQL scripts:
   ```bash
   mysql -u your_username -p your_database < scripts/init_db.sql
   ```

6. **Start Redis Server**
   Ensure Redis server is running on your system:
   ```bash
   redis-server
   ```

7. **Start Celery Worker**
   ```bash
   celery -A celery_tasks worker --loglevel=info
   ```

8. **Run the Application**
   ```bash
   python back_serv.py
   ```

## Verifying Installation

To verify that everything is working correctly:

1. Check if the Flask application is running:
   ```bash
   curl http://localhost:4093/health
   ```

2. Submit a test task:
   ```bash
   curl -X POST http://localhost:4093/submit_task \
        -H "Content-Type: application/json" \
        -d '{"task_type": "image_creation", "task_params": {}, "user_id": "test_user"}'
   ```

## Common Issues and Solutions

### Redis Connection Error
- Verify Redis is running: `redis-cli ping`
- Check Redis connection settings in `.env`

### Database Connection Error
- Verify MySQL is running
- Check database credentials in `.env`
- Ensure database and tables exist

### Celery Worker Not Starting
- Check Redis connection
- Verify Celery configuration
- Check log files for errors

## Next Steps

- Read the [API Documentation](api.md)
- Check out [Configuration Guide](configuration.md)
- Learn about [Deployment](deployment.md)
