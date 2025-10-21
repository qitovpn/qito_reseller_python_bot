#!/usr/bin/env python3
"""
Simple script to run both Telegram Bot and Web Admin Panel
Uses subprocess to run bot in background
"""

import subprocess
import sys
import time
import signal
import os
from web_admin import app, init_admin_tables
from database import init_database

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Stopping VPN Bot System...")
    if 'bot_process' in globals():
        bot_process.terminate()
        print("✅ Bot process stopped")
    print("✅ Web admin stopped")
    sys.exit(0)

if __name__ == '__main__':
    print("🚀 Starting VPN Bot System...")
    print("📊 Initializing database...")
    
    # Initialize database
    init_database()
    print("✅ Database initialized successfully!")
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n" + "="*50)
    print("🎯 Starting both services...")
    print("🤖 Telegram Bot: Starting in background...")
    print("🌐 Web Admin Panel: Starting on http://localhost:5000")
    print("="*50)
    print("\nPress Ctrl+C to stop both services")
    
    try:
        # Start bot as subprocess
        print("🤖 Starting Telegram Bot...")
        bot_process = subprocess.Popen([sys.executable, 'bot.py'], 
                                     stdout=None,  # Don't capture stdout - let it show
                                     stderr=None)  # Don't capture stderr - let it show
        
        # Give bot time to start
        time.sleep(3)
        
        # Check if bot is running
        if bot_process.poll() is None:
            print("✅ Telegram Bot started successfully!")
        else:
            print("❌ Telegram Bot failed to start!")
            print("Check the console output above for error details.")
        
        # Initialize admin tables
        init_admin_tables()
        
        # Start web admin
        print("🌐 Starting Web Admin Panel...")
        print("📱 Dashboard: http://localhost:5000")
        print("💰 Topup Management: http://localhost:5000/topup")
        print("💳 Payment Management: http://localhost:5000/payments")
        print("👥 User Management: http://localhost:5000/users")
        
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Error running system: {e}")
        if 'bot_process' in locals():
            bot_process.terminate()
        sys.exit(1)
