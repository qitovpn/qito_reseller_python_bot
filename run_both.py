#!/usr/bin/env python3
"""
Run both Telegram Bot and Web Admin Panel together
"""

import threading
import time
import os
import sys
from web_admin import app, init_admin_tables
from database import init_database

def run_bot():
    """Run the Telegram bot"""
    print("🤖 Starting Telegram Bot...")
    try:
        # Import and run the bot
        import bot
        print("✅ Telegram Bot started successfully!")
        print("📱 Bot is now running and listening for messages...")
        
        # Start the bot polling
        bot.bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"❌ Error starting Telegram Bot: {e}")
        import traceback
        traceback.print_exc()

def run_web_admin():
    """Run the web admin panel"""
    print("🌐 Starting Web Admin Panel...")
    try:
        init_admin_tables()
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ Error starting Web Admin Panel: {e}")

if __name__ == '__main__':
    print("🚀 Starting VPN Bot System...")
    print("📊 Initializing database...")
    
    # Initialize database
    init_database()
    print("✅ Database initialized successfully!")
    
    print("\n" + "="*50)
    print("🎯 Starting both services...")
    print("🤖 Telegram Bot: Running in background")
    print("🌐 Web Admin Panel: http://localhost:5000")
    print("📱 Dashboard: http://localhost:5000")
    print("💰 Topup Management: http://localhost:5000/topup")
    print("💳 Payment Management: http://localhost:5000/payments")
    print("👥 User Management: http://localhost:5000/users")
    print("="*50)
    print("\nPress Ctrl+C to stop both services")
    
    try:
        # Start bot in a separate thread
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Give bot time to start
        time.sleep(3)
        
        # Check if bot thread is still alive
        if bot_thread.is_alive():
            print("✅ Bot thread is running successfully!")
        else:
            print("❌ Bot thread failed to start!")
        
        # Run web admin in main thread
        print("🌐 Starting web admin panel...")
        run_web_admin()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping VPN Bot System...")
        print("✅ Both services stopped successfully!")
    except Exception as e:
        print(f"❌ Error running system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
