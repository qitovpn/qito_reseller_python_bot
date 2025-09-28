# VPN Bot - Expired Keys Cronjob

This document explains how to set up and use the automatic expired keys checking system for the VPN Bot.

## Overview

The cronjob system automatically checks for expired VPN keys and **deletes** them from the database. This ensures that expired keys are completely removed and administrators are notified.

## Features

- ✅ **Automatic Expiry Check**: Every 5 minutes check for expired keys
- ✅ **Complete Deletion**: Automatically deletes expired keys and plans
- ✅ **Orphaned Key Cleanup**: Removes unused VPN keys
- ✅ **Admin Notifications**: Sends alerts to administrators
- ✅ **Expiring Soon Alerts**: Warns about keys expiring in the next 3 days
- ✅ **Statistics**: Provides key usage statistics
- ✅ **Manual Commands**: Admin can manually check expired keys via bot

## Files

- `check_expired_keys.py` - Main cronjob script
- `setup_cronjob.sh` - Setup script for cronjob
- `database.py` - Contains expiry checking functions
- `bot.py` - Contains admin commands for manual checking

## Quick Setup

1. **Run the setup script:**
   ```bash
   ./setup_cronjob.sh
   ```

2. **Or manually add to crontab:**
   ```bash
   crontab -e
   ```
   Add this line:
   ```
   */5 * * * * cd /path/to/qitopybot && python3 check_expired_keys.py >> /var/log/vpn_bot_expired_keys.log 2>&1
   ```

## Manual Testing

Test the cronjob script manually:
```bash
python3 check_expired_keys.py
```

## Admin Bot Commands

Use these commands in the Telegram bot (admin only):

- `/expired` - Check and delete expired keys
- `/expiring` - Check keys expiring soon (next 7 days)
- `/keystats` - Get key statistics
- `/cleanup` - Clean up orphaned keys
- `/admin` - Show all admin commands

## Cronjob Schedule Options

- **Every 5 minutes** (default): `*/5 * * * *`
- **Every minute**: `* * * * *`
- **Every 10 minutes**: `*/10 * * * *`
- **Every 30 minutes**: `*/30 * * * *`
- **Every hour**: `0 * * * *`
- **Every 6 hours**: `0 */6 * * *`
- **Daily at 2 AM**: `0 2 * * *`

## What the Cronjob Does

1. **Checks Expired Keys**: Finds all active keys that have passed their expiry date
2. **Deletes Expired Data**: Completely removes expired user plans and VPN keys
3. **Cleans Orphaned Keys**: Removes VPN keys not assigned to any user plan
4. **Sends Notifications**: Alerts admin about deleted keys
5. **Checks Expiring Soon**: Identifies keys expiring in the next 3 days
6. **Logs Activity**: Records all actions in log files
7. **Provides Statistics**: Shows active plans and key usage statistics

## Database Functions

The following functions are available in `database.py`:

- `check_and_delete_expired_keys()` - Main function to check and delete expired keys
- `cleanup_orphaned_keys()` - Clean up orphaned VPN keys
- `get_expiring_soon_keys(days_ahead=3)` - Get keys expiring soon
- `get_expired_keys_stats()` - Get key statistics

## Log Files

- **Location**: `/var/log/vpn_bot_expired_keys.log` (or project directory)
- **Content**: Timestamps, expired key details, error messages
- **Rotation**: Consider setting up log rotation for long-term use

## Notifications

Currently, notifications are printed to console/log. To enable actual notifications:

1. **Telegram Notifications**: Modify `send_admin_notification()` in `check_expired_keys.py`
2. **Email Notifications**: Add email sending functionality
3. **Slack/Discord**: Add webhook notifications

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure the script is executable
   ```bash
   chmod +x check_expired_keys.py
   ```

2. **Python Path Issues**: Ensure Python can find the project modules
   ```bash
   export PYTHONPATH=/path/to/qitopybot:$PYTHONPATH
   ```

3. **Database Locked**: Check if the bot is running and accessing the database

4. **Cron Not Running**: Check cron service status
   ```bash
   sudo systemctl status cron
   ```

### Debug Mode

Run with verbose output:
```bash
python3 check_expired_keys.py 2>&1 | tee debug.log
```

## Security Considerations

- The cronjob runs with the same permissions as the user who set it up
- Ensure the database file has proper permissions
- Consider running as a dedicated user for better security
- Log files may contain sensitive information - secure them appropriately

## Monitoring

Monitor the cronjob by:

1. **Checking Logs**: `tail -f /var/log/vpn_bot_expired_keys.log`
2. **Using Bot Commands**: `/keystats` to see current statistics
3. **Database Queries**: Direct database inspection if needed

## Customization

You can customize:

- **Check Frequency**: Modify the cron schedule
- **Notification Methods**: Update `send_admin_notification()`
- **Expiry Threshold**: Change the "expiring soon" days
- **Log Format**: Modify the logging format in the script

## Support

For issues or questions:
1. Check the log files for error messages
2. Test the script manually first
3. Verify database permissions and connectivity
4. Check cron service status and configuration

