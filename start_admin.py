#!/usr/bin/env python3
"""
Admin Panel Startup Script
Run this to start the web admin panel for the VPN Bot
"""

import os
import sys
from web_admin import app, init_admin_tables

if __name__ == '__main__':
    print("🚀 Starting VPN Bot Admin Panel...")
    print("📊 Initializing database tables...")
    
    # Initialize admin tables
    init_admin_tables()
    
    print("✅ Database initialized successfully!")
    print("🌐 Admin panel will be available at: http://localhost:5000")
    print("📱 Dashboard: http://localhost:5000")
    print("💰 Topup Management: http://localhost:5000/topup")
    print("💳 Payment Management: http://localhost:5000/payments")
    print("👥 User Management: http://localhost:5000/users")
    print("\nPress Ctrl+C to stop the admin panel")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Admin panel stopped by user")
    except Exception as e:
        print(f"❌ Error starting admin panel: {e}")
        sys.exit(1)
