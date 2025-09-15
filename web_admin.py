from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
from datetime import datetime
from database import (init_plan_tables, create_plan, get_all_plans, get_plan, update_plan, 
                     delete_plan, add_vpn_keys, get_all_keys_for_plan, delete_vpn_key,
                     init_contact_tables, get_contact_config, update_contact_config)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this to a secure secret key

# Database file path
DB_FILE = 'bot_database.db'

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
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
            ('KBZ Pay', 'KBZ Bank mobile payment'),
            ('Wave Money', 'Wave Money mobile payment'),
            ('AYA Pay', 'AYA Bank mobile payment'),
            ('Cash Deposit', 'Cash deposit to bank account')
        ]
        cursor.executemany('INSERT INTO payment_methods (name, description) VALUES (?, ?)', default_payments)
    
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
    
    # Get topup options
    topup_options = conn.execute('SELECT * FROM topup_options ORDER BY credits').fetchall()
    
    # Get payment methods
    payment_methods = conn.execute('SELECT * FROM payment_methods ORDER BY name').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         users=users['count'], 
                         total_balance=total_balance['total'] or 0,
                         topup_options=topup_options,
                         payment_methods=payment_methods)

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
        
        conn = get_db_connection()
        conn.execute('INSERT INTO payment_methods (name, description) VALUES (?, ?)', 
                    (name, description))
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
        is_active = request.form.get('is_active') == 'on'
        
        conn.execute('UPDATE payment_methods SET name = ?, description = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (name, description, is_active, payment_id))
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
            'description': method['description']
        })
    
    return jsonify(methods)

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
        name = request.form['name']
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        
        create_plan(name, description, credits_required, duration_days)
        flash('Plan added successfully!', 'success')
        return redirect(url_for('plan_management'))
    
    return render_template('add_plan.html')

@app.route('/plans/edit/<int:plan_id>', methods=['GET', 'POST'])
def edit_plan(plan_id):
    """Edit plan"""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        credits_required = int(request.form['credits_required'])
        duration_days = int(request.form['duration_days'])
        is_active = request.form.get('is_active') == 'on'
        
        update_plan(plan_id, name, description, credits_required, duration_days, is_active)
        flash('Plan updated successfully!', 'success')
        return redirect(url_for('plan_management'))
    
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

if __name__ == '__main__':
    init_admin_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
