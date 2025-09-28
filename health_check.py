#!/usr/bin/env python3
"""
Health check script for the VPN Bot application
"""

import os
import sys
import sqlite3
import requests
from datetime import datetime

def check_database():
    """Check if database is accessible and has required tables"""
    try:
        db_file = 'bot_database.db'
        if not os.path.exists(db_file):
            print("❌ Database file not found")
            return False
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        required_tables = ['users', 'plans', 'user_plans']
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            print(f"❌ Missing required tables: {missing_tables}")
            return False
        
        conn.close()
        print("✅ Database is accessible and has required tables")
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_web_admin():
    """Check if web admin is accessible"""
    try:
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Web admin is accessible")
            return True
        else:
            print(f"❌ Web admin returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web admin check failed: {e}")
        return False

def check_scheduler():
    """Check if scheduler is running"""
    try:
        # Check if cron is running
        import subprocess
        result = subprocess.run(['pgrep', 'cron'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Cron daemon is running")
            return True
        else:
            # Check if alternative scheduler is running
            result = subprocess.run(['pgrep', '-f', 'scheduler.py'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Alternative scheduler is running")
                return True
            else:
                print("⚠️ No scheduler found (cron or alternative)")
                return False
                
    except Exception as e:
        print(f"❌ Scheduler check failed: {e}")
        return False

def main():
    """Main health check"""
    print(f"[{datetime.now()}] Starting health check...")
    
    checks = [
        ("Database", check_database),
        ("Web Admin", check_web_admin),
        ("Scheduler", check_scheduler)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        if check_func():
            passed += 1
        else:
            print(f"❌ {name} check failed")
    
    print(f"\n📊 Health Check Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ All systems healthy!")
        sys.exit(0)
    else:
        print("❌ Some systems are unhealthy!")
        sys.exit(1)

if __name__ == "__main__":
    main()