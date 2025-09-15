#!/usr/bin/env python3
"""
Health check script for QitopyBot
Used by Docker health check to verify the application is running
"""

import requests
import sys
import os

def check_health():
    """Check if the web admin panel is responding"""
    try:
        # Check if Flask web admin is responding
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Web admin panel is healthy")
            return True
        else:
            print(f"❌ Web admin panel returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)
