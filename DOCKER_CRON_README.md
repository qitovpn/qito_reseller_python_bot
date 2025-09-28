# VPN Bot - Docker Deployment with Cron Job

This document explains how to deploy the VPN Bot with automatic cron job functionality using Docker.

## Features

- ✅ **Automatic Cron Job**: Expired keys check every 5 minutes
- ✅ **Docker Container**: Easy deployment and management
- ✅ **Persistent Data**: Database and logs are preserved
- ✅ **Health Checks**: Automatic container health monitoring
- ✅ **APK File Management**: Web-based APK upload/download

## Quick Start

### 1. Environment Setup

Create a `.env` file with your configuration:

```bash
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_TELEGRAM_ID=your_admin_telegram_id_here

# Optional: Database path (default: bot_database.db)
DATABASE_PATH=bot_database.db
```

### 2. Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Verify Cron Job

```bash
# Check if cron job is running
docker exec qitopybot crontab -l

# View cron job logs
docker exec qitopybot tail -f /app/cronjob.log
```

## Docker Configuration

### Dockerfile Features

- **Base Image**: Python 3.12 slim
- **Cron Service**: Automatic expired keys checking
- **Security**: Non-root user execution
- **Dependencies**: All required packages included

### Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./data` | `/app/data` | Database persistence |
| `./logs` | `/app/logs` | Application logs |
| `./apk_files` | `/app/apk_files` | APK file storage |

## Cron Job Details

### Schedule
- **Frequency**: Every 5 minutes (`*/5 * * * *`)
- **Script**: `check_expired_keys.py`
- **Logs**: `/app/cronjob.log`

### What It Does
1. **Checks Expired Keys**: Finds keys past expiry date
2. **Deletes Expired Data**: Removes expired user plans and VPN keys
3. **Cleans Orphaned Keys**: Removes unused VPN keys
4. **Sends Notifications**: Alerts admin about deletions
5. **Logs Activity**: Records all actions

### Manual Cron Job Management

```bash
# View current cron jobs
docker exec qitopybot crontab -l

# Add new cron job
docker exec qitopybot bash -c "echo '0 2 * * * cd /app && python check_expired_keys.py' | crontab -"

# Remove all cron jobs
docker exec qitopybot crontab -r
```

## Monitoring

### Health Checks
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts
- **Start Period**: 40 seconds

### Log Files
- **Application Logs**: `./logs/`
- **Cron Job Logs**: `/app/cronjob.log`
- **Docker Logs**: `docker-compose logs`

### Monitoring Commands

```bash
# Check container status
docker-compose ps

# View real-time logs
docker-compose logs -f qitopybot

# Check cron job status
docker exec qitopybot pgrep cron

# View cron job logs
docker exec qitopybot tail -f /app/cronjob.log
```

## Troubleshooting

### Common Issues

1. **Cron Job Not Running**
   ```bash
   # Check if cron service is running
   docker exec qitopybot pgrep cron
   
   # Restart cron service
   docker exec qitopybot sudo service cron restart
   ```

2. **Permission Issues**
   ```bash
   # Check file permissions
   docker exec qitopybot ls -la /app/
   
   # Fix permissions
   docker exec qitopybot chown -R app:app /app/
   ```

3. **Database Issues**
   ```bash
   # Check database file
   docker exec qitopybot ls -la /app/data/
   
   # Verify database connection
   docker exec qitopybot python -c "import sqlite3; print('DB OK')"
   ```

### Debug Mode

```bash
# Run container in debug mode
docker run -it --rm qitopybot bash

# Check cron job manually
docker exec qitopybot python check_expired_keys.py

# View all processes
docker exec qitopybot ps aux
```

## Production Deployment

### Security Considerations

1. **Environment Variables**: Use secure `.env` file
2. **Database Backup**: Regular database backups
3. **Log Rotation**: Implement log rotation
4. **Updates**: Regular security updates

### Backup Strategy

```bash
# Backup database
docker exec qitopybot cp /app/data/bot_database.db /app/backup_$(date +%Y%m%d).db

# Backup logs
docker exec qitopybot tar -czf /app/logs_backup_$(date +%Y%m%d).tar.gz /app/logs/
```

### Scaling

For high-traffic scenarios:

1. **Database**: Consider PostgreSQL for better performance
2. **Load Balancing**: Use nginx for web admin
3. **Monitoring**: Implement Prometheus/Grafana
4. **Logging**: Use ELK stack for log management

## Maintenance

### Regular Tasks

1. **Log Cleanup**: Remove old log files
2. **Database Optimization**: Run VACUUM on SQLite
3. **Security Updates**: Update base image regularly
4. **Backup Verification**: Test backup restoration

### Update Process

```bash
# Pull latest changes
git pull

# Rebuild image
docker-compose build --no-cache

# Restart services
docker-compose down && docker-compose up -d
```

## Support

For issues or questions:
1. Check container logs: `docker-compose logs`
2. Verify cron job: `docker exec qitopybot crontab -l`
3. Test manually: `docker exec qitopybot python check_expired_keys.py`
4. Check file permissions and database connectivity
