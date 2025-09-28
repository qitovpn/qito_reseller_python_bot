#!/bin/bash

# Function to start cron service
start_cron() {
    echo "Starting cron service..."
    
    # Try to start cron service
    if command -v service > /dev/null; then
        sudo service cron start
    elif command -v systemctl > /dev/null; then
        sudo systemctl start cron
    else
        # Start cron daemon directly
        sudo cron
    fi
    
    # Wait a moment for cron to start
    sleep 2
    
    # Check if cron is running
    if pgrep cron > /dev/null; then
        echo "✅ Cron service started successfully"
        return 0
    else
        echo "❌ Failed to start cron service"
        return 1
    fi
}

# Function to setup cron job
setup_cron_job() {
    echo "Setting up cron job..."
    
    # Create cron job entry
    CRON_ENTRY="*/5 * * * * cd /app && /usr/local/bin/python3 check_expired_keys.py >> /app/cronjob.log 2>&1"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    
    echo "📋 Cron job added: $CRON_ENTRY"
}

# Start cron service
if start_cron; then
    # Setup cron job
    setup_cron_job
    
    # Display cron jobs
    echo "📋 Current cron jobs:"
    crontab -l
    
    # Start the main application
    echo "🚀 Starting VPN Bot application..."
    exec python run_both_simple.py
else
    echo "⚠️ Cron service failed to start, running without cron job..."
    echo "🚀 Starting VPN Bot application..."
    exec python run_both_simple.py
fi
