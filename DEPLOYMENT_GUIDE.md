# VPN Bot Deployment Guide

## 🚀 Digital App Platform Deployment

### Prerequisites
- Docker installed
- Digital App Platform account
- VPN Bot source code

### Step 1: Prepare Your Code

1. **Ensure all files are present:**
   ```bash
   ls -la
   # Should include: bot.py, web_admin.py, database.py, check_expired_keys.py
   # Dockerfile, docker-compose.yml, start_with_cron_fixed.sh
   ```

2. **Check file permissions:**
   ```bash
   chmod +x start_with_cron_fixed.sh
   chmod +x health_check.py
   ```

### Step 2: Build Docker Image

```bash
# Build the image
docker build -t vpn-bot .

# Test locally (optional)
docker run -p 5000:5000 vpn-bot
```

### Step 3: Deploy to Digital App Platform

1. **Push to your repository**
2. **Connect to Digital App Platform**
3. **Configure environment variables:**
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `ADMIN_TELEGRAM_ID`: Your admin Telegram ID

### Step 4: Verify Deployment

1. **Check application logs:**
   ```bash
   # Look for these messages:
   # ✅ Cron service started successfully
   # OR
   # ✅ Alternative scheduler started in background
   ```

2. **Test web admin:**
   - Visit: `https://your-app.digitalappplatform.com`
   - Login with admin credentials
   - Check database management

3. **Test Telegram bot:**
   - Send `/start` to your bot
   - Test basic functionality

## 🔧 Troubleshooting

### Cron Service Issues

**Problem:** `❌ Failed to start cron service`

**Solutions:**

1. **Check if running as root:**
   ```bash
   # In container
   whoami
   # Should show 'root' or have sudo access
   ```

2. **Manual cron start:**
   ```bash
   # Try starting cron manually
   cron -f &
   ```

3. **Use alternative scheduler:**
   - The app automatically falls back to Python-based scheduler
   - Check logs: `tail -f /app/scheduler.log`

### Database Issues

**Problem:** Database not accessible

**Solutions:**

1. **Check database file:**
   ```bash
   ls -la bot_database.db
   ```

2. **Check permissions:**
   ```bash
   chmod 664 bot_database.db
   chown app:app bot_database.db
   ```

3. **Initialize database:**
   ```python
   python -c "from database import init_admin_tables; init_admin_tables()"
   ```

### Web Admin Issues

**Problem:** Web admin not accessible

**Solutions:**

1. **Check if Flask is running:**
   ```bash
   netstat -tlnp | grep 5000
   ```

2. **Check logs:**
   ```bash
   tail -f /app/logs/web_admin.log
   ```

3. **Test locally:**
   ```bash
   curl http://localhost:5000/
   ```

## 📊 Monitoring

### Health Check

The application includes a health check script:

```bash
python health_check.py
```

**Expected output:**
```
✅ Database is accessible and has required tables
✅ Web admin is accessible
✅ Cron daemon is running
✅ All systems healthy!
```

### Log Files

Monitor these log files:

1. **Application logs:** `/app/logs/`
2. **Cron job logs:** `/app/cronjob.log`
3. **Scheduler logs:** `/app/scheduler.log`
4. **Web admin logs:** `/app/logs/web_admin.log`

### Key Metrics

- **Database size:** Check in web admin dashboard
- **Active users:** Monitor user count
- **Expired keys:** Check cron job execution
- **Memory usage:** Monitor container resources

## 🔄 Updates and Maintenance

### Updating the Application

1. **Pull latest code**
2. **Rebuild Docker image**
3. **Redeploy to platform**
4. **Verify functionality**

### Database Backup

1. **Use web admin:**
   - Go to Dashboard → Database Management
   - Click "Create Backup"
   - Download backup file

2. **Manual backup:**
   ```bash
   cp bot_database.db bot_database_backup_$(date +%Y%m%d_%H%M%S).db
   ```

### Monitoring Expired Keys

1. **Check cron job status:**
   ```bash
   tail -f /app/cronjob.log
   ```

2. **Manual execution:**
   ```bash
   python check_expired_keys.py
   ```

3. **Admin commands:**
   - `/expired` - Check expired keys
   - `/expiring` - Check expiring keys
   - `/keystats` - Key statistics

## 🛡️ Security Considerations

### Environment Variables

- Never commit tokens to repository
- Use platform's environment variable system
- Rotate tokens regularly

### Database Security

- Regular backups
- Monitor access logs
- Use strong admin passwords

### Container Security

- Run as non-root user when possible
- Keep base image updated
- Monitor resource usage

## 📞 Support

### Common Issues

1. **Cron not working:** Use alternative scheduler
2. **Database locked:** Check for running processes
3. **Web admin down:** Restart container
4. **Bot not responding:** Check Telegram token

### Debug Commands

```bash
# Check running processes
ps aux | grep python

# Check cron status
pgrep cron

# Check database
sqlite3 bot_database.db ".tables"

# Check logs
tail -f /app/logs/*.log
```

### Getting Help

1. Check application logs
2. Verify environment variables
3. Test components individually
4. Contact support with specific error messages
