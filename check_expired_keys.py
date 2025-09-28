#!/usr/bin/env python3
"""
Cronjob script to check for expired VPN keys and update their status.
This script should be run daily via cron to automatically manage expired keys.

Usage:
    python check_expired_keys.py

Cron setup (run daily at 2 AM):
    0 2 * * * cd /path/to/qitopybot && python check_expired_keys.py >> /var/log/vpn_bot_expired_keys.log 2>&1
"""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import check_and_delete_expired_keys, get_expiring_soon_keys, get_expired_keys_stats, cleanup_orphaned_keys

# Load environment variables
load_dotenv()

def send_admin_notification(message):
    """Send notification to admin (placeholder for actual notification system)"""
    print(f"[ADMIN NOTIFICATION] {message}")
    # Here you could integrate with:
    # - Telegram bot API to send message to admin
    # - Email notification
    # - Slack webhook
    # - Discord webhook
    # etc.

def main():
    """Main function to check and update expired keys"""
    print(f"[{datetime.now()}] Starting expired keys check...")
    
    try:
        # Check and delete expired keys
        deleted_count, deleted_details = check_and_delete_expired_keys()
        
        if deleted_count > 0:
            print(f"[{datetime.now()}] Found and deleted {deleted_count} expired keys")
            
            # Send admin notification
            notification_message = f"🗑️ **Expired Keys Cleanup**\n\n"
            notification_message += f"Deleted {deleted_count} expired VPN keys and plans:\n\n"
            
            for detail in deleted_details:
                notification_message += f"• User ID: {detail['user_id']}\n"
                notification_message += f"  Plan: {detail['plan_name']}\n"
                notification_message += f"  VPN Key: {detail['vpn_key'] or 'N/A'}\n"
                notification_message += f"  Expired: {detail['expiry_date']}\n\n"
            
            send_admin_notification(notification_message)
            
            # Log deleted keys
            for detail in deleted_details:
                print(f"  - User {detail['user_id']}: {detail['plan_name']} (expired: {detail['expiry_date']})")
        else:
            print(f"[{datetime.now()}] No expired keys found")
        
        # Clean up orphaned keys
        orphaned_count, orphaned_keys = cleanup_orphaned_keys()
        
        if orphaned_count > 0:
            print(f"[{datetime.now()}] Cleaned up {orphaned_count} orphaned keys")
            
            # Log orphaned keys
            for key in orphaned_keys:
                print(f"  - Orphaned key: {key['key_value']} (Plan ID: {key['plan_id']})")
        else:
            print(f"[{datetime.now()}] No orphaned keys found")
        
        # Check for keys expiring soon (next 3 days)
        expiring_soon = get_expiring_soon_keys(days_ahead=3)
        
        if expiring_soon:
            print(f"[{datetime.now()}] Found {len(expiring_soon)} keys expiring soon")
            
            # Send warning notification
            warning_message = f"⚠️ **Keys Expiring Soon**\n\n"
            warning_message += f"Found {len(expiring_soon)} keys expiring in the next 3 days:\n\n"
            
            for plan in expiring_soon:
                user_id, plan_name, expiry_date, username, first_name = plan
                user_display = f"@{username}" if username else f"{first_name} (ID: {user_id})"
                warning_message += f"• {user_display}\n"
                warning_message += f"  Plan: {plan_name}\n"
                warning_message += f"  Expires: {expiry_date}\n\n"
            
            send_admin_notification(warning_message)
            
            # Log expiring keys
            for plan in expiring_soon:
                user_id, plan_name, expiry_date, username, first_name = plan
                user_display = f"@{username}" if username else f"{first_name} (ID: {user_id})"
                print(f"  - {user_display}: {plan_name} (expires: {expiry_date})")
        
        # Get and log statistics
        stats = get_expired_keys_stats()
        print(f"[{datetime.now()}] Statistics:")
        print(f"  - Active plans: {stats['active_plans']}")
        print(f"  - Total VPN keys: {stats['total_keys']}")
        print(f"  - Used keys: {stats['used_keys']}")
        print(f"  - Available keys: {stats['available_keys']}")
        
        print(f"[{datetime.now()}] Expired keys check completed successfully")
        
    except Exception as e:
        error_message = f"❌ Error during expired keys check: {str(e)}"
        print(f"[{datetime.now()}] {error_message}")
        send_admin_notification(error_message)
        sys.exit(1)

if __name__ == "__main__":
    main()

