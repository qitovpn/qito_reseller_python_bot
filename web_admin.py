from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
from datetime import datetime
from database import (init_plan_tables, create_plan, get_all_plans, get_plan, update_plan, 
                     delete_plan, add_vpn_keys, get_all_keys_for_plan, delete_vpn_key,
                     init_contact_tables, get_contact_config, update_contact_config,
                     get_active_payment_methods_count, init_account_setup_tables,
                     get_account_setup_config, update_account_setup_config, get_all_account_setup_configs)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this to a secure secret key

# Database file path
DB_FILE = 'bot_database.db'

# APK upload configuration
UPLOAD_FOLDER = 'apk_files'
ALLOWED_EXTENSIONS = {'apk'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_admin_tables():
    """Initialize admin tables for topup options and payment info"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create topup_options table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS topup_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credits INTEGER NOT NULL,
            mmk_price INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create payment_methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            account_number TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add account_number column if it doesn't exist (for existing databases)
    cursor.execute("PRAGMA table_info(payment_methods)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'account_number' not in columns:
        cursor.execute('ALTER TABLE payment_methods ADD COLUMN account_number TEXT')
    
    # Insert default topup options if table is empty
    cursor.execute('SELECT COUNT(*) FROM topup_options')
    if cursor.fetchone()[0] == 0:
        default_topups = [
            (100, 10000),
            (200, 19000),
            (300, 28500),
            (500, 46000)
        ]
        cursor.executemany('INSERT INTO topup_options (credits, mmk_price) VALUES (?, ?)', default_topups)
    
    # Insert default payment methods if table is empty
    cursor.execute('SELECT COUNT(*) FROM payment_methods')
    if cursor.fetchone()[0] == 0:
        default_payments = [
            ('KBZ Pay', 'KBZ Bank mobile payment', '09XXXXXXXXX'),
            ('Wave Money', 'Wave Money mobile payment', '09XXXXXXXXX'),
            ('AYA Pay', 'AYA Bank mobile payment', '09XXXXXXXXX'),
            ('Cash Deposit', 'Cash deposit to bank account', 'Account Number: XXXX-XXXX-XXXX')
        ]
        cursor.executemany('INSERT INTO payment_methods (name, description, account_number) VALUES (?, ?, ?)', default_payments)
    
    # Initialize plan tables
    init_plan_tables()
    
    # Initialize contact tables
    init_contact_tables()
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Admin dashboard"""
    conn = get_db_connection()
    
    # Get user statistics
    users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
    total_balance = conn.execute('SELECT SUM(balance) as total FROM users').fetchone()
    
    # Get most purchased plans
    most_purchased_plans = conn.execute('''
        SELECT p.plan_id_number, p.name, COUNT(up.id) as purchase_count
        FROM plans p
        LEFT JOIN user_plans up ON p.id = up.plan_id
        WHERE p.is_active = 1
        GROUP BY p.id, p.plan_id_number, p.name
        ORDER BY purchase_count DESC
        LIMIT 5
    ''').fetchall()
    
    # Get recent purchases
    recent_purchases = conn.execute('''
        SELECT up.purchase_date, p.plan_id_number, p.name, u.telegram_id, u.username
        FROM user_plans up
        JOIN plans p ON up.plan_id = p.id
        JOIN users u ON up.user_id = u.telegram_id
        ORDER BY up.purchase_date DESC
        LIMIT 10
    ''').fetchall()
    
    # Get topup options
    topup_options = conn.execute('SELECT * FROM topup_options ORDER BY credits').fetchall()
    
    # Get payment methods
    payment_methods = conn.execute('SELECT * FROM payment_methods ORDER BY name').fetchall()
    
    # Get active payment methods count
    active_payment_methods_count = get_active_payment_methods_count()
    
    # Get QITO plans (plans with "QITO" in the name)
    qito_plans = conn.execute('''
        SELECT p.*, 
               COUNT(CASE WHEN vk.is_used = 0 THEN 1 END) as available_keys
        FROM plans p
        LEFT JOIN vpn_keys vk ON p.id = vk.plan_id
        WHERE p.name LIKE '%QITO%' AND p.is_active = 1
        GROUP BY p.id
        ORDER BY p.plan_id_number
    ''').fetchall()
    
    # Get QITO plans count
    qito_plans_count = conn.execute('''
        SELECT COUNT(*) FROM plans WHERE name LIKE '%QITO%' AND is_active = 1
    ''').fetchone()[0]
    
    # Get total available QITO keys count
    qito_keys_count = conn.execute('''
        SELECT COUNT(*) 
        FROM vpn_keys vk
        JOIN plans p ON vk.plan_id = p.id
        WHERE p.name LIKE '%QITO%' AND vk.is_used = 0
    ''').fetchone()[0]
    
    # Get database file information
    db_info = None
    if os.path.exists(DB_FILE):
        stat = os.stat(DB_FILE)
        db_info = {
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    conn.close()
    
    return render_template('dashboard.html', 
                         users=users['count'], 
                         total_balance=total_balance['total'] or 0,
                         most_purchased_plans=most_purchased_plans,
                         recent_purchases=recent_purchases,
                         topup_options=topup_options,
                         payment_methods=payment_methods,
                         active_payment_methods_count=active_payment_methods_count,
                         qito_plans=qito_plans,
                         qito_plans_count=qito_plans_count,
                         qito_keys_count=qito_keys_count,
                         db_info=db_info)

@app.route('/topup')
def topup_management():
    """Topup options management"""
    conn = get_db_connection()
    topup_options = conn.execute('SELECT * FROM topup_options ORDER BY credits').fetchall()
    conn.close()
    return render_template('topup_management.html', topup_options=topup_options)

@app.route('/topup/add', methods=['GET', 'POST'])
def add_topup():
    """Add new topup option"""
    if request.method == 'POST':
        credits = request.form['credits']
        mmk_price = request.form['mmk_price']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO topup_options (credits, mmk_price) VALUES (?, ?)', 
                    (credits, mmk_price))
        conn.commit()
        conn.close()
        
        flash('Topup option added successfully!', 'success')
        return redirect(url_for('topup_management'))
    
    return render_template('add_topup.html')

@app.route('/topup/edit/<int:topup_id>', methods=['GET', 'POST'])
def edit_topup(topup_id):
    """Edit topup option"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        credits = request.form['credits']
        mmk_price = request.form['mmk_price']
        is_active = request.form.get('is_active') == 'on'
        
        conn.execute('UPDATE topup_options SET credits = ?, mmk_price = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (credits, mmk_price, is_active, topup_id))
        conn.commit()
        conn.close()
        
        flash('Topup option updated successfully!', 'success')
        return redirect(url_for('topup_management'))
    
    topup = conn.execute('SELECT * FROM topup_options WHERE id = ?', (topup_id,)).fetchone()
    conn.close()
    
    if topup is None:
        flash('Topup option not found!', 'error')
        return redirect(url_for('topup_management'))
    
    return render_template('edit_topup.html', topup=topup)

@app.route('/topup/delete/<int:topup_id>')
def delete_topup(topup_id):
    """Delete topup option"""
    conn = get_db_connection()
    conn.execute('DELETE FROM topup_options WHERE id = ?', (topup_id,))
    conn.commit()
    conn.close()
    
    flash('Topup option deleted successfully!', 'success')
    return redirect(url_for('topup_management'))

@app.route('/payments')
def payment_management():
    """Payment methods management"""
    conn = get_db_connection()
    payment_methods = conn.execute('SELECT * FROM payment_methods ORDER BY name').fetchall()
    conn.close()
    return render_template('payment_management.html', payment_methods=payment_methods)

@app.route('/payments/add', methods=['GET', 'POST'])
def add_payment():
    """Add new payment method"""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        account_number = request.form.get('account_number', '')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO payment_methods (name, description, account_number) VALUES (?, ?, ?)', 
                    (name, description, account_number))
        conn.commit()
        conn.close()
        
        flash('Payment method added successfully!', 'success')
        return redirect(url_for('payment_management'))
    
    return render_template('add_payment.html')

@app.route('/payments/edit/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(payment_id):
    """Edit payment method"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        account_number = request.form.get('account_number', '')
        is_active = request.form.get('is_active') == 'on'
        
        conn.execute('UPDATE payment_methods SET name = ?, description = ?, account_number = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (name, description, account_number, is_active, payment_id))
        conn.commit()
        conn.close()
        
        flash('Payment method updated successfully!', 'success')
        return redirect(url_for('payment_management'))
    
    payment = conn.execute('SELECT * FROM payment_methods WHERE id = ?', (payment_id,)).fetchone()
    conn.close()
    
    if payment is None:
        flash('Payment method not found!', 'error')
        return redirect(url_for('payment_management'))
    
    return render_template('edit_payment.html', payment=payment)

@app.route('/payments/delete/<int:payment_id>')
def delete_payment(payment_id):
    """Delete payment method"""
    conn = get_db_connection()
    conn.execute('DELETE FROM payment_methods WHERE id = ?', (payment_id,))
    conn.commit()
    conn.close()
    
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('payment_management'))

@app.route('/users')
def user_management():
    """User management"""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('user_management.html', users=users)

@app.route('/api/topup-options')
def api_topup_options():
    """API endpoint to get topup options for bot"""
    conn = get_db_connection()
    topup_options = conn.execute('SELECT * FROM topup_options WHERE is_active = 1 ORDER BY credits').fetchall()
    conn.close()
    
    options = []
    for option in topup_options:
        options.append({
            'id': option['id'],
            'credits': option['credits'],
            'mmk_price': option['mmk_price']
        })
    
    return jsonify(options)

@app.route('/api/payment-methods')
def api_payment_methods():
    """API endpoint to get payment methods for bot"""
    conn = get_db_connection()
    payment_methods = conn.execute('SELECT * FROM payment_methods WHERE is_active = 1 ORDER BY name').fetchall()
    conn.close()
    
    methods = []
    for method in payment_methods:
        methods.append({
            'id': method['id'],
            'name': method['name'],
            'description': method['description'],
            'account_number': method['account_number']
        })
    
    return jsonify(methods)

# User Management API endpoints
@app.route('/api/user/<int:user_id>')
def api_get_user(user_id):
    """API endpoint to get user details with purchased plans"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user:
        # Get user's purchased plans
        user_plans = conn.execute('''
            SELECT up.id, p.plan_id_number, p.name, p.description, vk.key_value, 
                   up.purchase_date, up.expiry_date, up.status
            FROM user_plans up
            JOIN plans p ON up.plan_id = p.id
            LEFT JOIN vpn_keys vk ON up.vpn_key_id = vk.id
            WHERE up.user_id = ?
            ORDER BY up.purchase_date DESC
        ''', (user['telegram_id'],)).fetchall()
        
        conn.close()
        
        # Format user plans
        plans = []
        for plan in user_plans:
            plans.append({
                'id': plan[0],
                'plan_id_number': plan[1],
                'name': plan[2],
                'description': plan[3],
                'vpn_key': plan[4],
                'purchase_date': plan[5],
                'expiry_date': plan[6],
                'status': plan[7]
            })
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'telegram_id': user['telegram_id'],
                'username': user['username'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'balance': user['balance'],
                'created_at': user['created_at'],
                'updated_at': user['updated_at'],
                'purchased_plans': plans
            }
        })
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/user/update-balance', methods=['POST'])
def api_update_user_balance():
    """API endpoint to update user balance"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_balance = float(data.get('balance'))
        
        if not user_id or new_balance < 0:
            return jsonify({'success': False, 'message': 'Invalid data provided'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        user = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Update user balance
        # Round to 0 decimal places to ensure whole numbers (no floating-point precision issues)
        cursor.execute('''
            UPDATE users 
            SET balance = ROUND(?, 0), updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (new_balance, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'User balance updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating balance: {str(e)}'})

@app.route('/api/users/all')
def api_get_all_users():
    """API endpoint to get all users for search"""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    user_list = []
    for user in users:
        user_list.append({
            'id': user['id'],
            'telegram_id': user['telegram_id'],
            'username': user['username'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'balance': user['balance'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at']
        })
    
    return jsonify({'success': True, 'users': user_list})

# Plan Management Routes
@app.route('/plans')
def plan_management():
    """Plan management page"""
    plans = get_all_plans()
    return render_template('plan_management.html', plans=plans)

@app.route('/plans/add', methods=['GET', 'POST'])
def add_plan():
    """Add new plan"""
    if request.method == 'POST':
        plan_id_number = request.form['plan_id_number']
        name = request.form['name']
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        
        try:
            create_plan(plan_id_number, name, description, credits_required, duration_days)
            flash('Plan added successfully!', 'success')
            return redirect(url_for('plan_management'))
        except sqlite3.IntegrityError:
            flash('Plan ID number already exists! Please use a different ID number.', 'error')
            return render_template('add_plan.html')
    
    return render_template('add_plan.html')

@app.route('/plans/edit/<int:plan_id>', methods=['GET', 'POST'])
def edit_plan(plan_id):
    """Edit plan"""
    if request.method == 'POST':
        plan_id_number = request.form['plan_id_number']
        name = request.form['name']
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        is_active = request.form.get('is_active') == 'on'
        
        try:
            update_plan(plan_id, plan_id_number, name, description, credits_required, duration_days, is_active)
            flash('Plan updated successfully!', 'success')
            return redirect(url_for('plan_management'))
        except sqlite3.IntegrityError:
            flash('Plan ID number already exists! Please use a different ID number.', 'error')
            plan = get_plan(plan_id)
            return render_template('edit_plan.html', plan=plan)
    
    plan = get_plan(plan_id)
    if plan is None:
        flash('Plan not found!', 'error')
        return redirect(url_for('plan_management'))
    
    return render_template('edit_plan.html', plan=plan)

@app.route('/plans/delete/<int:plan_id>')
def delete_plan_route(plan_id):
    """Delete plan"""
    delete_plan(plan_id)
    flash('Plan deleted successfully!', 'success')
    return redirect(url_for('plan_management'))

@app.route('/plans/<int:plan_id>/keys')
def plan_keys(plan_id):
    """Manage keys for a plan"""
    plan = get_plan(plan_id)
    if plan is None:
        flash('Plan not found!', 'error')
        return redirect(url_for('plan_management'))
    
    keys = get_all_keys_for_plan(plan_id)
    return render_template('plan_keys.html', plan=plan, keys=keys)

@app.route('/plans/<int:plan_id>/keys/add', methods=['POST'])
def add_plan_keys(plan_id):
    """Add keys to a plan"""
    keys_text = request.form['keys']
    keys_list = [key.strip() for key in keys_text.split('\n') if key.strip()]
    
    if keys_list:
        add_vpn_keys(plan_id, keys_list)
        flash(f'{len(keys_list)} keys added successfully!', 'success')
    else:
        flash('No valid keys provided!', 'error')
    
    return redirect(url_for('plan_keys', plan_id=plan_id))

@app.route('/keys/delete/<int:key_id>')
def delete_key(key_id):
    """Delete a VPN key"""
    delete_vpn_key(key_id)
    flash('Key deleted successfully!', 'success')
    return redirect(request.referrer or url_for('plan_management'))

# QITO Plan Management Routes
@app.route('/qito')
def qito_plan_management():
    """QITO plan management page"""
    conn = get_db_connection()
    qito_plans = conn.execute('''
        SELECT p.*, 
               COALESCE(p.device_limit, 1) as device_limit
        FROM plans p
        WHERE p.name LIKE '%QITO%'
        ORDER BY p.plan_id_number
    ''').fetchall()
    conn.close()
    return render_template('qito_plan_management.html', qito_plans=qito_plans)

@app.route('/qito/add', methods=['GET', 'POST'])
def add_qito_plan():
    """Add new QITO plan"""
    if request.method == 'POST':
        plan_id_number = request.form['plan_id_number']
        name = f"QITO {request.form['name']}"  # Automatically prefix with QITO
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        device_limit = int(request.form.get('device_limit', 1))
        
        try:
            create_plan(plan_id_number, name, description, credits_required, duration_days, device_limit)
            flash('QITO plan added successfully!', 'success')
            return redirect(url_for('qito_plan_management'))
        except sqlite3.IntegrityError:
            flash('Plan ID number already exists! Please use a different ID number.', 'error')
            return render_template('add_qito_plan.html')
    
    return render_template('add_qito_plan.html')

@app.route('/qito/edit/<int:plan_id>', methods=['GET', 'POST'])
def edit_qito_plan(plan_id):
    """Edit QITO plan"""
    if request.method == 'POST':
        plan_id_number = request.form['plan_id_number']
        name = f"QITO {request.form['name']}"  # Automatically prefix with QITO
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        device_limit = int(request.form.get('device_limit', 1))
        is_active = request.form.get('is_active') == 'on'
        
        try:
            update_plan(plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, device_limit)
            flash('QITO plan updated successfully!', 'success')
            return redirect(url_for('qito_plan_management'))
        except sqlite3.IntegrityError:
            flash('Plan ID number already exists! Please use a different ID number.', 'error')
            plan = get_plan(plan_id)
            return render_template('edit_qito_plan.html', plan=plan)
    
    plan = get_plan(plan_id)
    if plan is None:
        flash('QITO plan not found!', 'error')
        return redirect(url_for('qito_plan_management'))
    
    return render_template('edit_qito_plan.html', plan=plan)

@app.route('/qito/delete/<int:plan_id>')
def delete_qito_plan(plan_id):
    """Delete QITO plan"""
    delete_plan(plan_id)
    flash('QITO plan deleted successfully!', 'success')
    return redirect(url_for('qito_plan_management'))


@app.route('/qito/statistics')
def qito_statistics():
    """QITO statistics page"""
    conn = get_db_connection()
    
    # Get QITO plan statistics
    qito_stats = conn.execute('''
        SELECT 
            COUNT(DISTINCT p.id) as total_plans,
            COUNT(CASE WHEN p.is_active = 1 THEN 1 END) as active_plans,
            SUM(COALESCE(p.device_limit, 1)) as total_device_slots
        FROM plans p
        WHERE p.name LIKE '%QITO%'
    ''').fetchone()
    
    # Get QITO purchase statistics
    qito_purchases = conn.execute('''
        SELECT 
            DATE(up.purchase_date) as purchase_date,
            COUNT(*) as purchase_count
        FROM user_plans up
        JOIN plans p ON up.plan_id = p.id
        WHERE p.name LIKE '%QITO%'
        GROUP BY DATE(up.purchase_date)
        ORDER BY purchase_date DESC
        LIMIT 30
    ''').fetchall()
    
    # Get most popular QITO plans
    popular_qito_plans = conn.execute('''
        SELECT 
            p.plan_id_number,
            p.name,
            COUNT(up.id) as purchase_count
        FROM plans p
        LEFT JOIN user_plans up ON p.id = up.plan_id
        WHERE p.name LIKE '%QITO%'
        GROUP BY p.id
        ORDER BY purchase_count DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('qito_statistics.html', 
                         qito_stats=qito_stats,
                         qito_purchases=qito_purchases,
                         popular_qito_plans=popular_qito_plans)

# Contact Management Routes
@app.route('/contact')
def contact_management():
    """Contact configuration management page"""
    contacts = get_contact_config()
    return render_template('contact_management.html', contacts=contacts)

@app.route('/contact/edit/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    """Edit contact configuration"""
    if request.method == 'POST':
        contact_value = request.form['contact_value']
        is_active = request.form.get('is_active') == 'on'
        display_order = int(request.form.get('display_order', 0))
        
        update_contact_config(contact_id, contact_value, is_active, display_order)
        flash('Contact configuration updated successfully!', 'success')
        return redirect(url_for('contact_management'))
    
    # Get contact details
    contacts = get_contact_config()
    contact = next((c for c in contacts if c[0] == contact_id), None)
    
    if contact is None:
        flash('Contact configuration not found!', 'error')
        return redirect(url_for('contact_management'))
    
    return render_template('edit_contact.html', contact=contact)

# APK Management Routes
@app.route('/apk')
def apk_management():
    """APK management page"""
    # Check if APK file exists
    apk_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest.apk')
    apk_exists = os.path.exists(apk_path)
    
    apk_info = None
    if apk_exists:
        stat = os.stat(apk_path)
        apk_info = {
            'name': 'latest.apk',
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    return render_template('apk_management.html', apk_info=apk_info)

@app.route('/apk/upload', methods=['POST'])
def upload_apk():
    """Upload APK file"""
    if 'apk_file' not in request.files:
        flash('No file selected!', 'error')
        return redirect(url_for('apk_management'))
    
    file = request.files['apk_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('apk_management'))
    
    if file and allowed_file(file.filename):
        # Create upload directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save file as latest.apk
        filename = secure_filename('latest.apk')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        flash('APK file uploaded successfully!', 'success')
    else:
        flash('Invalid file type! Only APK files are allowed.', 'error')
    
    return redirect(url_for('apk_management'))

@app.route('/apk/delete', methods=['POST'])
def delete_apk():
    """Delete APK file"""
    apk_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest.apk')
    
    if os.path.exists(apk_path):
        os.remove(apk_path)
        flash('APK file deleted successfully!', 'success')
    else:
        flash('APK file not found!', 'error')
    
    return redirect(url_for('apk_management'))

@app.route('/apk/download')
def download_apk():
    """Download APK file"""
    from flask import send_file
    
    apk_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest.apk')
    
    if os.path.exists(apk_path):
        return send_file(apk_path, as_attachment=True, download_name='vpn_app.apk')
    else:
        flash('APK file not found!', 'error')
        return redirect(url_for('apk_management'))

@app.route('/database/download')
def download_database():
    """Download database file"""
    from flask import send_file
    import shutil
    from datetime import datetime
    
    try:
        # Check if database file exists
        if not os.path.exists(DB_FILE):
            flash('Database file not found!', 'error')
            return redirect(url_for('dashboard'))
        
        # Create a backup copy with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'bot_database_backup_{timestamp}.db'
        backup_path = os.path.join('/tmp', backup_filename)
        
        # Copy database file to temp location
        shutil.copy2(DB_FILE, backup_path)
        
        # Send the backup file
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/database/backup', methods=['POST'])
def backup_database():
    """Create a backup of the database"""
    from datetime import datetime
    import shutil
    
    try:
        # Check if database file exists
        if not os.path.exists(DB_FILE):
            flash('Database file not found!', 'error')
            return redirect(url_for('dashboard'))
        
        # Create backup directory if it doesn't exist
        backup_dir = 'database_backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'bot_database_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file to backup location
        shutil.copy2(DB_FILE, backup_path)
        
        # Get backup file size
        backup_size = os.path.getsize(backup_path)
        backup_size_mb = round(backup_size / (1024 * 1024), 2)
        
        flash(f'Database backup created successfully! File: {backup_filename} ({backup_size_mb} MB)', 'success')
        
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/database/restore', methods=['POST'])
def restore_database():
    """Restore database from uploaded file"""
    from werkzeug.utils import secure_filename
    import shutil
    from datetime import datetime
    
    try:
        # Check if file was uploaded
        if 'database_file' not in request.files:
            flash('No database file selected!', 'error')
            return redirect(url_for('dashboard'))
        
        file = request.files['database_file']
        if file.filename == '':
            flash('No database file selected!', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if file is a database file
        if not file.filename.lower().endswith('.db'):
            flash('Invalid file type! Only .db files are allowed.', 'error')
            return redirect(url_for('dashboard'))
        
        # Check file size (basic validation)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size == 0:
            flash('Uploaded file is empty!', 'error')
            return redirect(url_for('dashboard'))
        
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            flash('File too large! Maximum size is 100MB.', 'error')
            return redirect(url_for('dashboard'))
        
        # Create backup of current database before restore
        if os.path.exists(DB_FILE):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'bot_database_before_restore_{timestamp}.db'
            backup_dir = 'database_backups'
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, backup_filename)
            shutil.copy2(DB_FILE, backup_path)
            flash(f'Current database backed up as: {backup_filename}', 'info')
        
        # Save uploaded file as new database
        temp_path = DB_FILE + '.temp'
        file.save(temp_path)
        
        # Verify the uploaded file before replacing current database
        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if not tables:
                os.remove(temp_path)
                flash('Uploaded database appears to be empty or corrupted!', 'error')
                return redirect(url_for('dashboard'))
            
            # If verification passes, replace the current database
            shutil.move(temp_path, DB_FILE)
            flash(f'Database restored successfully! Found {len(tables)} tables.', 'success')
            
        except Exception as e:
            # Clean up temp file if verification fails
            if os.path.exists(temp_path):
                os.remove(temp_path)
            flash(f'Uploaded database appears to be corrupted: {str(e)}', 'error')
            return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Error restoring database: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/database/backups')
def list_backups():
    """List all database backups"""
    backup_dir = 'database_backups'
    
    if not os.path.exists(backup_dir):
        return render_template('database_backups.html', backups=[])
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db'):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            backups.append({
                'filename': filename,
                'size': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'path': filepath
            })
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('database_backups.html', backups=backups)

@app.route('/database/backup/<filename>/download')
def download_backup(filename):
    """Download a specific backup file"""
    from flask import send_file
    import os
    
    backup_dir = 'database_backups'
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        flash('Backup file not found!', 'error')
        return redirect(url_for('list_backups'))
    
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

@app.route('/database/backup/<filename>/restore', methods=['POST'])
def restore_from_backup(filename):
    """Restore database from a specific backup"""
    import shutil
    from datetime import datetime
    
    try:
        backup_dir = 'database_backups'
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found!', 'error')
            return redirect(url_for('list_backups'))
        
        # Create backup of current database before restore
        if os.path.exists(DB_FILE):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup_filename = f'bot_database_before_restore_{timestamp}.db'
            current_backup_path = os.path.join(backup_dir, current_backup_filename)
            shutil.copy2(DB_FILE, current_backup_path)
            flash(f'Current database backed up as: {current_backup_filename}', 'info')
        
        # Copy backup to current database location
        shutil.copy2(backup_path, DB_FILE)
        
        # Verify the restored database
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if not tables:
                flash('Restored database appears to be empty or corrupted!', 'error')
                return redirect(url_for('list_backups'))
            
            flash(f'Database restored successfully from {filename}! Found {len(tables)} tables.', 'success')
            
        except Exception as e:
            flash(f'Restored database appears to be corrupted: {str(e)}', 'error')
            return redirect(url_for('list_backups'))
        
    except Exception as e:
        flash(f'Error restoring database: {str(e)}', 'error')
    
    return redirect(url_for('list_backups'))

@app.route('/database/backup/<filename>/delete', methods=['POST'])
def delete_backup(filename):
    """Delete a specific backup file"""
    import os
    
    try:
        backup_dir = 'database_backups'
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found!', 'error')
            return redirect(url_for('list_backups'))
        
        os.remove(backup_path)
        flash(f'Backup {filename} deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
    
    return redirect(url_for('list_backups'))

# Account Setup Management Routes
@app.route('/account-setup')
def account_setup():
    """Account setup configuration page"""
    configs = get_all_account_setup_configs()
    return render_template('account_setup.html', configs=configs)

@app.route('/account-setup/update', methods=['POST'])
def update_account_setup():
    """Update account setup configuration"""
    config_key = request.form.get('config_key')
    config_value = request.form.get('config_value')
    description = request.form.get('description', '')
    
    if not config_key or not config_value:
        flash('Configuration key and value are required!', 'error')
        return redirect(url_for('account_setup'))
    
    try:
        update_account_setup_config(config_key, config_value, description)
        flash(f'Configuration "{config_key}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')
    
    return redirect(url_for('account_setup'))

if __name__ == '__main__':
    init_admin_tables()
    init_account_setup_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
