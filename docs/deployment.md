# Deployment Guide

This guide covers how to deploy Back.Serv in various environments.

## Production Deployment Checklist

### 1. Security
- [ ] Set strong passwords
- [ ] Configure SSL/TLS
- [ ] Set up firewall rules
- [ ] Remove debug mode
- [ ] Secure all endpoints
- [ ] Configure CORS properly
- [ ] Set up rate limiting

### 2. Environment
- [ ] Set up production environment variables
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Configure backup system
- [ ] Set up alerting

### 3. Performance
- [ ] Configure connection pools
- [ ] Set up caching
- [ ] Configure worker processes
- [ ] Set up load balancing
- [ ] Configure database indexes

## Deployment Options

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t back.serv .
   ```

2. **Run with Docker Compose**
   ```yaml
   version: '3'
   services:
     web:
       build: .
       ports:
         - "4093:4093"
       env_file:
         - .env
       depends_on:
         - redis
         - mysql
     
     redis:
       image: redis:latest
       ports:
         - "6379:6379"
     
     mysql:
       image: mysql:8
       env_file:
         - .env
       volumes:
         - mysql_data:/var/lib/mysql
     
     celery:
       build: .
       command: celery -A celery_tasks worker --loglevel=info
       env_file:
         - .env
       depends_on:
         - redis
         - mysql
   
   volumes:
     mysql_data:
   ```

### Traditional Server Deployment

1. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Supervisor**
   ```ini
   [program:backserv]
   directory=/path/to/back.serv
   command=/path/to/back.serv/venv/bin/gunicorn back_serv:flask_app -w 4 -b 0.0.0.0:4093
   user=backserv
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/backserv/err.log
   stdout_logfile=/var/log/backserv/out.log
   
   [program:backserv_celery]
   directory=/path/to/back.serv
   command=/path/to/back.serv/venv/bin/celery -A celery_tasks worker --loglevel=info
   user=backserv
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/backserv_celery/err.log
   stdout_logfile=/var/log/backserv_celery/out.log
   ```

3. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your_domain.com;
   
       location / {
           proxy_pass http://localhost:4093;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Monitoring and Maintenance

### Health Monitoring

1. **Set up Prometheus monitoring**
   ```yaml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'backserv'
       static_configs:
         - targets: ['localhost:4093']
   ```

2. **Configure Grafana dashboard**
   - System metrics
   - Application metrics
   - Task queue metrics

### Backup Strategy

1. **Database Backup**
   ```bash
   # Daily backup script
   #!/bin/bash
   mysqldump -u user -p database | gzip > backup-$(date +%Y%m%d).sql.gz
   ```

2. **Log Rotation**
   ```conf
   /var/log/backserv/*.log {
       daily
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 backserv backserv
   }
   ```

## Scaling Strategies

### Horizontal Scaling

1. **Add More Workers**
   ```bash
   celery -A celery_tasks worker --loglevel=info --concurrency=4
   ```

2. **Load Balancer Configuration**
   ```nginx
   upstream backserv {
       server 127.0.0.1:4093;
       server 127.0.0.1:4094;
       server 127.0.0.1:4095;
   }
   ```

### Vertical Scaling

1. **Increase Resources**
   - CPU cores
   - RAM
   - Disk space

2. **Optimize Configuration**
   - Database connection pool
   - Worker processes
   - Cache size

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check network connectivity
   - Verify firewall rules
   - Check service status

2. **Performance Issues**
   - Monitor system resources
   - Check log files
   - Analyze database queries

3. **Worker Issues**
   - Check Celery worker status
   - Verify Redis connection
   - Check task queue
