# Configuration Guide

This document describes how to configure Back.Serv for different environments and use cases.

## Environment Variables

Back.Serv uses environment variables for configuration. Create a `.env` file in the root directory by copying `.env.example`:

```bash
cp .env.example .env
```

### Available Configuration Options

#### Flask Configuration
```env
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_PORT=4093
FLASK_HOST=0.0.0.0
```

#### Database Configuration
```env
DB_HOST=your_db_host
DB_PORT=your_db_port
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
```

#### Redis Configuration
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB_BROKER=0
REDIS_DB_BACKEND=1
```

#### AI Server Configuration
```env
AI_SERVER_URL=http://your.ai.server.url:port
AI_SERVER_STATUS_ENDPOINT=/check_status
```

#### Task Configuration
```env
TASK_TIMEOUT_SECONDS=300
MAX_RETRIES=3
```

## Configuration Profiles

### Development
```env
FLASK_ENV=development
FLASK_DEBUG=1
```

### Production
```env
FLASK_ENV=production
FLASK_DEBUG=0
```

### Testing
```env
FLASK_ENV=testing
FLASK_DEBUG=1
DB_NAME=test_db
```

## Logging Configuration

Logging is configured in `back_serv.py`. Default configuration:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Log Levels
- DEBUG: Detailed information for debugging
- INFO: General information about system operation
- WARNING: Warning messages for potential issues
- ERROR: Error messages for serious problems
- CRITICAL: Critical issues that require immediate attention

## Celery Configuration

Celery configuration is defined in `celery_tasks.py`:

```python
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

### Task Queue Settings

- Default queue: Used for most tasks
- Priority queue: For urgent tasks
- Scheduled tasks: Configured using `beat_schedule`

## Security Considerations

1. **Environment Variables**
   - Never commit `.env` file to version control
   - Use strong passwords
   - Rotate secrets regularly

2. **Database Security**
   - Use least privilege principle for database users
   - Enable SSL for database connections
   - Regular backup strategy

3. **API Security**
   - Rate limiting
   - Input validation
   - Error handling without exposing internal details

## Performance Tuning

### Database Connection Pool
```python
pool_size=5
max_overflow=10
pool_timeout=30
pool_recycle=1800
```

### Redis Connection Pool
```python
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    max_connections=100
)
```

### Celery Worker Configuration
```bash
celery -A celery_tasks worker --loglevel=info --concurrency=4
```

## Monitoring

### Health Check Endpoint
- `/health`: Returns system health status
- Monitors: Database, Redis, AI servers

### Metrics
- Task processing time
- Queue length
- Error rates
- Server resource usage

## Backup and Recovery

1. **Database Backup**
   ```bash
   mysqldump -u user -p database > backup.sql
   ```

2. **Environment Configuration**
   - Keep secure copies of `.env`
   - Document all custom configurations

3. **Recovery Procedures**
   - Database restoration
   - Configuration restoration
   - Service restart procedures
