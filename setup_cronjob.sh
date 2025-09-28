#!/bin/bash

# Setup script for VPN Bot expired keys cronjob
# This script helps set up automatic checking of expired keys

echo "🔧 Setting up VPN Bot expired keys cronjob..."

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRONJOB_SCRIPT="$SCRIPT_DIR/check_expired_keys.py"

# Make the cronjob script executable
chmod +x "$CRONJOB_SCRIPT"

echo "✅ Made cronjob script executable"

# Create log directory if it doesn't exist
LOG_DIR="/var/log"
if [ ! -d "$LOG_DIR" ]; then
    echo "⚠️  Log directory $LOG_DIR doesn't exist. Using project directory for logs."
    LOG_DIR="$SCRIPT_DIR/logs"
    mkdir -p "$LOG_DIR"
fi

# Create the cronjob entry (every 5 minutes) - using virtual environment
CRON_ENTRY="*/5 * * * * cd $SCRIPT_DIR && $SCRIPT_DIR/venv/bin/python3 $CRONJOB_SCRIPT >> $LOG_DIR/vpn_bot_expired_keys.log 2>&1"

echo ""
echo "📋 Cronjob setup instructions:"
echo "================================"
echo ""
echo "1. Add the following line to your crontab:"
echo "   $CRON_ENTRY"
echo ""
echo "2. To edit your crontab, run:"
echo "   crontab -e"
echo ""
echo "3. This will run the expired keys check every 5 minutes"
echo ""
echo "4. Alternative schedules:"
echo "   - Every minute: * * * * *"
echo "   - Every 10 minutes: */10 * * * *"
echo "   - Every 30 minutes: */30 * * * *"
echo "   - Every hour: 0 * * * *"
echo "   - Every 6 hours: 0 */6 * * *"
echo "   - Daily at 2 AM: 0 2 * * *"
echo ""
echo "5. To view cron logs (if available):"
echo "   tail -f $LOG_DIR/vpn_bot_expired_keys.log"
echo ""
echo "6. To test the script manually:"
echo "   cd $SCRIPT_DIR && python3 $CRONJOB_SCRIPT"
echo ""

# Check if crontab exists and offer to add automatically
if command -v crontab &> /dev/null; then
    echo "🤖 Would you like me to add the cronjob automatically? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
echo "✅ Cronjob added successfully!"
echo "📅 The expired keys check will run every 5 minutes"
    else
        echo "ℹ️  You can add the cronjob manually later using the instructions above."
    fi
else
    echo "⚠️  crontab command not found. Please install cron or add the job manually."
fi

echo ""
echo "🎯 Setup complete! The cronjob will:"
echo "   - Check for expired keys daily"
echo "   - Update expired key statuses"
echo "   - Send notifications to admin"
echo "   - Log all activities"
echo ""
echo "📞 For support or questions, check the bot documentation."
