import sqlite3
import os
from datetime import datetime

# Database file path
DB_FILE = 'bot_database.db'

def init_database():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def user_exists(telegram_id):
    """Check if user exists in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def create_user(telegram_id, username=None, first_name=None, last_name=None):
    """Create a new user with balance 0"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, balance)
            VALUES (?, ?, ?, ?, 0.0)
        ''', (telegram_id, username, first_name, last_name))
        
        conn.commit()
        print(f"✅ New user created: {telegram_id}")
        return True
    except sqlite3.IntegrityError:
        print(f"⚠️ User {telegram_id} already exists")
        return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False
    finally:
        conn.close()

def get_user_balance(telegram_id):
    """Get user's current balance"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0.0

def ensure_user_exists(telegram_id, username=None, first_name=None, last_name=None):
    """Check if user exists, if not create with balance 0"""
    if not user_exists(telegram_id):
        create_user(telegram_id, username, first_name, last_name)
        return False  # User was created
    return True  # User already existed

def get_topup_options():
    """Get all active topup options from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT credits, mmk_price FROM topup_options WHERE is_active = 1 ORDER BY credits')
    options = cursor.fetchall()
    
    conn.close()
    return options

def get_payment_methods():
    """Get all active payment methods from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, description FROM payment_methods WHERE is_active = 1 ORDER BY name')
    methods = cursor.fetchall()
    
    conn.close()
    return methods

def init_payment_tables():
    """Initialize payment-related tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create pending_payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            credits INTEGER NOT NULL,
            mmk_price INTEGER NOT NULL,
            payment_proof_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_pending_payment(user_id, credits, mmk_price, payment_proof_file_id=None):
    """Create a pending payment record"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO pending_payments (user_id, credits, mmk_price, payment_proof_file_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, credits, mmk_price, payment_proof_file_id))
    
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return payment_id

def get_pending_payment(payment_id):
    """Get pending payment by ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM pending_payments WHERE id = ?', (payment_id,))
    payment = cursor.fetchone()
    
    conn.close()
    return payment

def update_payment_status(payment_id, status):
    """Update payment status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE pending_payments 
        SET status = ?, processed_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (status, payment_id))
    
    conn.commit()
    conn.close()

def add_user_balance(telegram_id, credits):
    """Add credits to user balance"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Convert credits to dollars (assuming 1 credit = $0.01)
    dollars = credits * 0.01
    
    cursor.execute('''
        UPDATE users 
        SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP 
        WHERE telegram_id = ?
    ''', (dollars, telegram_id))
    
    conn.commit()
    conn.close()

def init_plan_tables():
    """Initialize plan and key management tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            credits_required INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create vpn_keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vpn_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            key_value TEXT NOT NULL,
            is_used BOOLEAN DEFAULT 0,
            used_by_user_id INTEGER,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans (id),
            FOREIGN KEY (used_by_user_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Create user_plans table (to track user purchases)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            vpn_key_id INTEGER,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiry_date TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users (telegram_id),
            FOREIGN KEY (plan_id) REFERENCES plans (id),
            FOREIGN KEY (vpn_key_id) REFERENCES vpn_keys (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Plan management functions
def create_plan(name, description, credits_required, duration_days):
    """Create a new plan"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO plans (name, description, credits_required, duration_days)
        VALUES (?, ?, ?, ?)
    ''', (name, description, credits_required, duration_days))
    
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return plan_id

def get_all_plans():
    """Get all plans"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM plans ORDER BY credits_required')
    plans = cursor.fetchall()
    
    conn.close()
    return plans

def get_active_plans():
    """Get active plans"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM plans WHERE is_active = 1 ORDER BY credits_required')
    plans = cursor.fetchall()
    
    conn.close()
    return plans

def get_plan(plan_id):
    """Get plan by ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM plans WHERE id = ?', (plan_id,))
    plan = cursor.fetchone()
    
    conn.close()
    return plan

def update_plan(plan_id, name, description, credits_required, duration_days, is_active):
    """Update plan"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE plans 
        SET name = ?, description = ?, credits_required = ?, duration_days = ?, 
            is_active = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (name, description, credits_required, duration_days, is_active, plan_id))
    
    conn.commit()
    conn.close()

def delete_plan(plan_id):
    """Delete plan"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM plans WHERE id = ?', (plan_id,))
    conn.commit()
    conn.close()

# VPN Key management functions
def add_vpn_keys(plan_id, keys_list):
    """Add multiple VPN keys for a plan"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for key_value in keys_list:
        cursor.execute('''
            INSERT INTO vpn_keys (plan_id, key_value)
            VALUES (?, ?)
        ''', (plan_id, key_value.strip()))
    
    conn.commit()
    conn.close()

def get_available_keys(plan_id):
    """Get available (unused) keys for a plan"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, key_value FROM vpn_keys 
        WHERE plan_id = ? AND is_used = 0 
        ORDER BY created_at ASC
    ''', (plan_id,))
    keys = cursor.fetchall()
    
    conn.close()
    return keys

def get_all_keys_for_plan(plan_id):
    """Get all keys for a plan (used and unused)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, key_value, is_used, used_by_user_id, used_at, created_at 
        FROM vpn_keys 
        WHERE plan_id = ? 
        ORDER BY created_at DESC
    ''', (plan_id,))
    keys = cursor.fetchall()
    
    conn.close()
    return keys

def assign_key_to_user(plan_id, user_id):
    """Assign an available key to a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get an available key
    cursor.execute('''
        SELECT id, key_value FROM vpn_keys 
        WHERE plan_id = ? AND is_used = 0 
        ORDER BY created_at ASC LIMIT 1
    ''', (plan_id,))
    key = cursor.fetchone()
    
    if key:
        key_id, key_value = key
        
        # Mark key as used
        cursor.execute('''
            UPDATE vpn_keys 
            SET is_used = 1, used_by_user_id = ?, used_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (user_id, key_id))
        
        # Get plan details
        cursor.execute('SELECT duration_days FROM plans WHERE id = ?', (plan_id,))
        plan = cursor.fetchone()
        duration_days = plan[0] if plan else 30
        
        # Create user plan record
        cursor.execute('''
            INSERT INTO user_plans (user_id, plan_id, vpn_key_id, expiry_date)
            VALUES (?, ?, ?, datetime('now', '+{} days'))
        '''.format(duration_days), (user_id, plan_id, key_id))
        
        conn.commit()
        conn.close()
        
        return key_value
    else:
        conn.close()
        return None

def get_user_plans(user_id):
    """Get user's purchased plans"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT up.id, p.name, p.description, vk.key_value, up.purchase_date, up.expiry_date, up.status
        FROM user_plans up
        JOIN plans p ON up.plan_id = p.id
        LEFT JOIN vpn_keys vk ON up.vpn_key_id = vk.id
        WHERE up.user_id = ?
        ORDER BY up.purchase_date DESC
    ''', (user_id,))
    plans = cursor.fetchall()
    
    conn.close()
    return plans

def delete_vpn_key(key_id):
    """Delete a VPN key"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM vpn_keys WHERE id = ?', (key_id,))
    conn.commit()
    conn.close()

def check_low_key_plans(min_keys=10):
    """Check for plans with low key availability"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all active plans with their available key counts
    cursor.execute('''
        SELECT p.id, p.name, COUNT(vk.id) as available_keys
        FROM plans p
        LEFT JOIN vpn_keys vk ON p.id = vk.plan_id AND vk.is_used = 0
        WHERE p.is_active = 1
        GROUP BY p.id, p.name
        HAVING available_keys < ?
        ORDER BY available_keys ASC
    ''', (min_keys,))
    
    low_key_plans = cursor.fetchall()
    conn.close()
    
    return low_key_plans

def get_plan_key_statistics():
    """Get key statistics for all plans"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            p.id,
            p.name,
            COUNT(vk.id) as total_keys,
            COUNT(CASE WHEN vk.is_used = 0 THEN 1 END) as available_keys,
            COUNT(CASE WHEN vk.is_used = 1 THEN 1 END) as used_keys
        FROM plans p
        LEFT JOIN vpn_keys vk ON p.id = vk.plan_id
        WHERE p.is_active = 1
        GROUP BY p.id, p.name
        ORDER BY available_keys ASC
    ''')
    
    stats = cursor.fetchall()
    conn.close()
    
    return stats

def init_contact_tables():
    """Initialize contact configuration table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create contact_config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_type TEXT NOT NULL UNIQUE,
            contact_value TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default contact configurations if table is empty
    cursor.execute('SELECT COUNT(*) FROM contact_config')
    if cursor.fetchone()[0] == 0:
        default_contacts = [
            ('telegram', '@VPNSupportBot', 1, 1),
            ('telegram_admin', '@AdminUsername', 1, 2),
            ('email', 'support@vpnservice.com', 1, 3),
            ('phone', '+95-XXX-XXX-XXXX', 1, 4),
            ('website', 'https://vpnservice.com', 1, 5),
            ('response_time', 'Within 2 hours', 1, 6),
            ('business_hours', 'Monday - Friday: 9:00 AM - 6:00 PM (UTC)', 1, 7)
        ]
        cursor.executemany('''
            INSERT INTO contact_config (contact_type, contact_value, is_active, display_order)
            VALUES (?, ?, ?, ?)
        ''', default_contacts)
    
    conn.commit()
    conn.close()

# Contact configuration functions
def get_contact_config():
    """Get all contact configurations"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, contact_type, contact_value, is_active, display_order, created_at, updated_at
        FROM contact_config 
        ORDER BY display_order ASC, contact_type ASC
    ''')
    contacts = cursor.fetchall()
    
    conn.close()
    return contacts

def get_active_contact_config():
    """Get active contact configurations"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT contact_type, contact_value
        FROM contact_config 
        WHERE is_active = 1
        ORDER BY display_order ASC, contact_type ASC
    ''')
    contacts = cursor.fetchall()
    
    conn.close()
    return contacts

def update_contact_config(contact_id, contact_value, is_active, display_order):
    """Update contact configuration"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE contact_config 
        SET contact_value = ?, is_active = ?, display_order = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (contact_value, is_active, display_order, contact_id))
    
    conn.commit()
    conn.close()

def get_contact_by_type(contact_type):
    """Get contact value by type"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT contact_value FROM contact_config 
        WHERE contact_type = ? AND is_active = 1
    ''', (contact_type,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None
