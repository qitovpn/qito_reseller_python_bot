#!/bin/bash

# Function to start cron service
start_cron() {
    echo "Starting cron service..."
    
    # Check if we're running as root
    if [ "$EUID" -eq 0 ]; then
        echo "Running as root, starting cron service..."
        
        # Start cron daemon in background
        cron -f &
        CRON_PID=$!
        
        # Wait a moment for cron to start
        sleep 3
        
        # Check if cron is running
        if pgrep cron > /dev/null; then
            echo "✅ Cron service started successfully (PID: $CRON_PID)"
            return 0
        else
            echo "❌ Failed to start cron service"
            return 1
        fi
    else
        echo "Not running as root, trying alternative methods..."
        
        # Try to start cron with sudo
        if sudo cron -f & 2>/dev/null; then
            sleep 3
            if pgrep cron > /dev/null; then
                echo "✅ Cron service started with sudo"
                return 0
            fi
        fi
        
        echo "❌ Failed to start cron service (not root and sudo failed)"
        return 1
    fi
}

# Function to start alternative scheduler
start_alternative_scheduler() {
    echo "🔄 Starting alternative scheduler (Python-based)..."
    
    # Create a simple Python scheduler script
    cat > /app/scheduler.py << 'EOF'
#!/usr/bin/env python3
import time
import subprocess
import os
import sys
from datetime import datetime

def run_expired_keys_check():
    """Run the expired keys check script"""
    try:
        print(f"[{datetime.now()}] Running expired keys check...")
        result = subprocess.run([
            sys.executable, 
            '/app/check_expired_keys.py'
        ], capture_output=True, text=True, cwd='/app')
        
        if result.returncode == 0:
            print(f"[{datetime.now()}] Expired keys check completed successfully")
            if result.stdout:
                print(f"Output: {result.stdout}")
        else:
            print(f"[{datetime.now()}] Expired keys check failed: {result.stderr}")
            
    except Exception as e:
        print(f"[{datetime.now()}] Error running expired keys check: {e}")

def main():
    """Main scheduler loop"""
    print(f"[{datetime.now()}] Starting alternative scheduler (every 5 minutes)...")
    
    while True:
        try:
            run_expired_keys_check()
            # Wait 5 minutes (300 seconds)
            time.sleep(300)
        except KeyboardInterrupt:
            print(f"[{datetime.now()}] Scheduler stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Scheduler error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
EOF
    
    # Make it executable
    chmod +x /app/scheduler.py
    
    # Start scheduler in background
    nohup python /app/scheduler.py > /app/scheduler.log 2>&1 &
    SCHEDULER_PID=$!
    echo "✅ Alternative scheduler started in background (PID: $SCHEDULER_PID)"
}

# Function to check if cron jobs are working
check_cron_status() {
    echo "Checking cron status..."
    
    # Check if cron is running
    if pgrep cron > /dev/null; then
        echo "✅ Cron daemon is running"
        
        # Check if our cron job exists
        if [ -f /etc/cron.d/vpn-bot ]; then
            echo "✅ VPN Bot cron job file exists"
            cat /etc/cron.d/vpn-bot
        else
            echo "⚠️ VPN Bot cron job file not found"
        fi
        
        return 0
    else
        echo "❌ Cron daemon is not running"
        return 1
    fi
}

# Main execution
echo "🚀 Starting VPN Bot with scheduling..."

# Try to start cron service
if start_cron; then
    echo "📋 Cron service started, checking status..."
    check_cron_status
    
    # Start the main application
    echo "🚀 Starting VPN Bot application with cron..."
    exec python run_both_simple.py
else
    echo "⚠️ Cron service failed to start, using alternative scheduler..."
    
    # Start alternative scheduler
    start_alternative_scheduler
    
    # Start the main application
    echo "🚀 Starting VPN Bot application with alternative scheduler..."
    exec python run_both_simple.py
fi
