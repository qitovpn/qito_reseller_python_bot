import os
import sqlite3
import telebot
import requests
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from database import (init_database, ensure_user_exists, get_user_balance, get_topup_options, 
                     get_payment_methods, init_payment_tables, create_pending_payment, 
                     get_pending_payment, update_payment_status, add_user_balance,
                     init_plan_tables, get_active_plans, get_plan, assign_key_to_user, 
                     get_user_plans, get_available_keys, check_low_key_plans, get_plan_key_statistics,
                     init_contact_tables, get_active_contact_config, check_and_delete_expired_keys,
                     get_expiring_soon_keys, get_expired_keys_stats, cleanup_orphaned_keys)

# Load environment variables
load_dotenv()

# QITO API Configuration
QITO_API_URL = os.getenv('QITO_API_URL', 'http://localhost:3000/api/users')

# Initialize database
init_database()
init_payment_tables()
init_plan_tables()
init_contact_tables()

# Initialize bot with token from environment variable
bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))

# Get admin telegram ID
ADMIN_TELEGRAM_ID = os.getenv('ADMIN_TELEGRAM_ID')

def send_low_key_notification():
    """Send notification to admin about plans with low key availability"""
    if not ADMIN_TELEGRAM_ID:
        return
    
    low_key_plans = check_low_key_plans(min_keys=10)
    
    if low_key_plans:
        notification_text = "⚠️ **LOW KEY ALERT**\n\n"
        notification_text += "The following plans have fewer than 10 available keys:\n\n"
        
        for plan_id, plan_name, available_keys in low_key_plans:
            notification_text += f"🔑 **{plan_name}**\n"
            notification_text += f"Available Keys: {available_keys}\n\n"
        
        notification_text += "Please add more keys to these plans to avoid service interruption."
        
        try:
            bot.send_message(ADMIN_TELEGRAM_ID, notification_text, parse_mode='Markdown')
        except Exception as e:
            print(f"Failed to send low key notification: {e}")

def check_and_notify_low_keys():
    """Check for low keys and send notification if needed"""
    try:
        send_low_key_notification()
    except Exception as e:
        print(f"Error checking low keys: {e}")

def create_qito_user_api(device_limit, duration_days):
    """Create QITO user via API"""
    try:
        from datetime import datetime, timedelta
        # Calculate expiry date
        expiry_date = datetime.now() + timedelta(days=duration_days)
        expiry_date_str = expiry_date.strftime('%Y-%m-%dT%H:%M')
        
        # Prepare API request data
        api_data = {
            "expire_date": expiry_date_str,
            "device_limit": device_limit
        }
        
        # Make API request
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
        }
        
        response = requests.post(QITO_API_URL, headers=headers, json=api_data, timeout=30)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            print(f"API request failed with status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating QITO user via API: {e}")
        return None

# Create the main menu (Reply Keyboard)
def create_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = KeyboardButton("👤 ကျွန်ုပ်၏ credit")
    item2 = KeyboardButton("💳 ငွေဖြည့်")
    item3 = KeyboardButton("VPN Key ဝယ်ရန်")
    item4 = KeyboardButton("📋 ကျွန်ုပ်၏ပက်ကေ့ချ်")
    item5 = KeyboardButton("📞 ဆက်သွယ်ရန်")
    item6 = KeyboardButton("🗝 QITO Key")
    markup.add(item1, item2)
    markup.add(item3, item6)
    markup.add(item4, item5)
    return markup

# Create inline keyboard for quick actions
def create_inline_menu():
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("Option A", callback_data='option_a_selected')
    button2 = InlineKeyboardButton("Visit Google", url='https://www.google.com')
    button3 = InlineKeyboardButton("Visit GitHub", url='https://github.com')
    button4 = InlineKeyboardButton("🎲 Random Number", callback_data='inline_random')
    markup.row(button1, button2)
    markup.row(button3, button4)
    return markup

# Create inline keyboard for info actions
def create_info_inline_menu():
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("📊 My Info", callback_data='get_user_info')
    button2 = InlineKeyboardButton("🔗 Visit Google", url='https://www.google.com')
    button3 = InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
    markup.row(button1, button2)
    markup.add(button3)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    
    """Handle /start command"""
    # Check if user exists, if not create with balance 0
    user_existed = ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    if user_existed:
        welcome_text = f"ပြန်လည်ကြိုဆိုပါတယ်၊ {message.from_user.first_name}! 👋\n\nကျွန်ုပ်တို့၏ VPN ဝန်ဆောင်မှုဘော့သို့ ကြိုဆိုပါတယ်! အောက်ပါမီနူးမှ ရွေးချယ်ပါ။"
    else:
        welcome_text = f"မင်္ဂလာပါ {message.from_user.first_name}! 👋\n\nကျွန်ုပ်တို့၏ VPN ဝန်ဆောင်မှုဘော့သို့ ကြိုဆိုပါတယ်! သင့်အကောင့်ကို ငွေလက်ကျန် $0.00 ဖြင့် ဖန်တီးပေးပါပြီ။ အောက်ပါမီနူးမှ ရွေးချယ်ပါ။"
    
    bot.reply_to(message, welcome_text, reply_markup=create_main_menu())

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command"""
    help_text = """
🤖 **VPN ဝန်ဆောင်မှုဘော့ ညွှန်ကြားချက်များ:**

/start - ဘော့ကို စတင်ပြီး မူလမီနူးကိုြသပါ
/help - ဤအကူအညီစာကိုြသပါ

**မူလမီနူး ရွေးချယ်စရာများ:**
• 👤 ကျွန်ုပ်၏ credit - သင့်အကောင့်ငွေလက်ကျန်နှင့် ငွေလွှဲမှုများကို ကြည့်ရှုပါ
• 💳 ငွေဖြည့် - သင့်အကောင့်သို့ ငွေထည့်ပါ
• VPN Key ဝယ်ရန် - VPN ပက်ကေ့ချ်များကို ကြည့်ရှုပြီး ဝယ်ယူပါ
• 📋 ကျွန်ုပ်၏ပက်ကေ့ချ် - ဝယ်ယူထားသော ပက်ကေ့ချ်များနှင့် VPN Keyများကို ကြည့်ရှုပါ
• 📞 ဆက်သွယ်ရန် - ဖောက်သည်ဝန်ဆောင်မှုနှင့် ဆက်သွယ်ရန်အချက်အလက်များကို ရယူပါ

**အင်္ဂါရပ်များ:**
• အပြန်အလှန်ပြုလုပ်နိုင်သော ပြန်လည်အသုံးပြုနိုင်သော ကီးဘုတ်များ
• မြန်ဆန်သောလုပ်ဆောင်မှုများအတွက် အတွင်းပိုင်းကီးဘုတ်များ
• အကောင့်ငွေလက်ကျန် စီမံခန့်ခွဲမှု
• ပက်ကေ့ချ်ဝယ်ယူမှုနှင့် VPN Keyပေးအပ်မှု
• ဖောက်သည်ဝန်ဆောင်မှု ပေါင်းစပ်မှု

    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown', reply_markup=create_main_menu())

# Admin commands are handled below in the existing admin handler

@bot.message_handler(commands=['keys'])
def check_keys_command(message):
    """Check key availability status"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    stats = get_plan_key_statistics()
    
    if not stats:
        bot.send_message(message.chat.id, "📊 **Key Status**\n\nNo active plans found.", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
        return
    
    status_text = "📊 **Key Availability Status**\n\n"
    
    for plan_id, plan_name, total_keys, available_keys, used_keys in stats:
        status_text += f"🔑 **{plan_name}**\n"
        status_text += f"Total Keys: {total_keys}\n"
        status_text += f"Available: {available_keys}\n"
        status_text += f"Used: {used_keys}\n"
        
        if available_keys < 10:
            status_text += "⚠️ **LOW KEYS!**\n"
        
        status_text += "\n"
    
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown', reply_markup=create_main_menu())

@bot.message_handler(commands=['lowkeys'])
def check_low_keys_command(message):
    """Check for plans with low key count"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    send_low_key_notification()
    bot.send_message(message.chat.id, "✅ Low key check completed. Check your messages for alerts.", 
                    reply_markup=create_main_menu())

@bot.message_handler(commands=['expired'])
def check_expired_keys_command(message):
    """Check and delete expired keys"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    try:
        deleted_count, deleted_details = check_and_delete_expired_keys()
        
        if deleted_count > 0:
            deleted_text = f"🗑️ **Expired Keys Deleted**\n\n"
            deleted_text += f"Found and deleted {deleted_count} expired keys and plans:\n\n"
            
            for detail in deleted_details:
                deleted_text += f"• User ID: {detail['user_id']}\n"
                deleted_text += f"  Plan: {detail['plan_name']}\n"
                deleted_text += f"  VPN Key: {detail['vpn_key'] or 'N/A'}\n"
                deleted_text += f"  Expired: {detail['expiry_date']}\n\n"
            
            bot.send_message(message.chat.id, deleted_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "✅ No expired keys found. All keys are still active.", 
                           reply_markup=create_main_menu())
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error checking expired keys: {str(e)}", 
                       reply_markup=create_main_menu())

@bot.message_handler(commands=['expiring'])
def check_expiring_keys_command(message):
    """Check keys expiring soon"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    try:
        expiring_soon = get_expiring_soon_keys(days_ahead=7)  # Check next 7 days
        
        if expiring_soon:
            expiring_text = f"⚠️ **Keys Expiring Soon**\n\n"
            expiring_text += f"Found {len(expiring_soon)} keys expiring in the next 7 days:\n\n"
            
            for plan in expiring_soon:
                user_id, plan_name, expiry_date, username, first_name = plan
                user_display = f"@{username}" if username else f"{first_name} (ID: {user_id})"
                expiring_text += f"• {user_display}\n"
                expiring_text += f"  Plan: {plan_name}\n"
                expiring_text += f"  Expires: {expiry_date}\n\n"
            
            bot.send_message(message.chat.id, expiring_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "✅ No keys expiring in the next 7 days.", 
                           reply_markup=create_main_menu())
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error checking expiring keys: {str(e)}", 
                       reply_markup=create_main_menu())

@bot.message_handler(commands=['keystats'])
def get_key_statistics_command(message):
    """Get key statistics"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    try:
        stats = get_expired_keys_stats()
        
        stats_text = f"📊 **Key Statistics**\n\n"
        stats_text += f"• Active Plans: {stats['active_plans']}\n"
        stats_text += f"• Total VPN Keys: {stats['total_keys']}\n"
        stats_text += f"• Used Keys: {stats['used_keys']}\n"
        stats_text += f"• Available Keys: {stats['available_keys']}\n\n"
        
        # Calculate usage percentage
        if stats['total_keys'] > 0:
            usage_percentage = (stats['used_keys'] / stats['total_keys']) * 100
            stats_text += f"• Key Usage Rate: {usage_percentage:.1f}%\n"
        
        bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', 
                       reply_markup=create_main_menu())
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error getting key statistics: {str(e)}", 
                       reply_markup=create_main_menu())

@bot.message_handler(commands=['cleanup'])
def cleanup_orphaned_keys_command(message):
    """Clean up orphaned keys"""
    if str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.send_message(message.chat.id, "❌ Unauthorized access.", reply_markup=create_main_menu())
        return
    
    try:
        deleted_count, deleted_keys = cleanup_orphaned_keys()
        
        if deleted_count > 0:
            cleanup_text = f"🧹 **Orphaned Keys Cleanup**\n\n"
            cleanup_text += f"Deleted {deleted_count} orphaned keys:\n\n"
            
            for key in deleted_keys:
                cleanup_text += f"• Key: {key['key_value']}\n"
                cleanup_text += f"  Plan ID: {key['plan_id']}\n\n"
            
            bot.send_message(message.chat.id, cleanup_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "✅ No orphaned keys found. All keys are properly assigned.", 
                           reply_markup=create_main_menu())
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error cleaning up orphaned keys: {str(e)}", 
                       reply_markup=create_main_menu())

@bot.message_handler(commands=['admin'])
def admin_commands(message):
    """Handle admin commands"""
    if str(message.from_user.id) == str(ADMIN_TELEGRAM_ID):
        # Get pending payments
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, credits, mmk_price, status, created_at 
            FROM pending_payments 
            WHERE status = 'pending' 
            ORDER BY created_at DESC
        ''')
        pending_payments = cursor.fetchall()
        conn.close()
        
        if pending_payments:
            admin_text = "🔔 **Pending Payments:**\n\n"
            for payment in pending_payments:
                payment_id, user_id, credits, mmk_price, status, created_at = payment
                admin_text += f"**Payment #{payment_id}**\n"
                admin_text += f"User ID: {user_id}\n"
                admin_text += f"Amount: {credits} Credits ({mmk_price:,} MMK)\n"
                admin_text += f"Status: {status}\n"
                admin_text += f"Created: {created_at}\n\n"
        else:
            admin_text = "✅ No pending payments at the moment.\n\n"
        
        # Check for low keys
        low_key_plans = check_low_key_plans(min_keys=10)
        if low_key_plans:
            admin_text += "⚠️ **Low Key Alert:**\n"
            for plan_id, plan_name, available_keys in low_key_plans:
                admin_text += f"• {plan_name}: {available_keys} keys\n"
            admin_text += "\n"
        
        admin_text += "**Admin Commands:**\n"
        admin_text += "/keys - Check key availability status\n"
        admin_text += "/lowkeys - Check for plans with low key count\n"
        admin_text += "/expired - Check and delete expired keys\n"
        admin_text += "/expiring - Check keys expiring soon\n"
        admin_text += "/keystats - Get key statistics\n"
        admin_text += "/cleanup - Clean up orphaned keys"
        
        bot.send_message(message.chat.id, admin_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")

@bot.message_handler(commands=['info'])
def send_info(message):
    """Handle /info command"""
    info_text = f"""
📊 **Bot Information:**

**User Info:**
• Name: {message.from_user.first_name} {message.from_user.last_name or ''}
• Username: @{message.from_user.username or 'Not set'}
• User ID: {message.from_user.id}
• Language: {message.from_user.language_code or 'Not set'}

**Chat Info:**
• Chat ID: {message.chat.id}
• Chat Type: {message.chat.type}
    """
    bot.send_message(message.chat.id, info_text, parse_mode='Markdown', reply_markup=create_main_menu())

@bot.message_handler(commands=['random'])
def send_random(message):
    """Handle /random command"""
    import random
    random_num = random.randint(1, 100)
    
    bot.send_message(message.chat.id, f"🎲 Your random number is: **{random_num}**", 
                    parse_mode='Markdown', reply_markup=create_main_menu())

# Handle menu button messages
@bot.message_handler(func=lambda message: message.text == "👤 ကျွန်ုပ်၏ credit")
def handle_my_balance(message):
    """Handle My Balance button"""
    # Ensure user exists in database
    ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get actual balance from database
    current_balance = get_user_balance(message.from_user.id)
    credits = int(current_balance * 100)  # Convert to credits (1 dollar = 100 credits)
    
    balance_text = f"""👤 သင့်အကောင့်ငွေလက်ကျန်

• လက်ကျန် Credits: {credits:,}
• အကောင့်အခြေအနေ: ✅ လုပ်ဆောင်နေ

အကောင့်အချက်အလက်:
• အသုံးပြုသူ ID: {message.from_user.id}
• အသုံးပြုသူအမည်: @{message.from_user.username or 'မသတ်မှတ်ထား'}

သင့်အကောင့်သို့ ငွေထပ်ထည့်ရန် 💳 ငွေဖြည့် ကို အသုံးပြုပါ။"""
    
    bot.send_message(message.chat.id, balance_text, reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: message.text == "💳 ငွေဖြည့်")
def handle_topup(message):
    """Handle Topup button"""
    # Get topup options from database
    topup_options = get_topup_options()
    payment_methods = get_payment_methods()
    
    if not topup_options:
        bot.send_message(message.chat.id, "❌ လက်ရှိတွင် ငွေဖြည့်ရွေးချယ်စရာများ မရှိပါ။ ကျေးဇူးပြု၍ ဝန်ဆောင်မှုကို ဆက်သွယ်ပါ။", 
                        reply_markup=create_main_menu())
        return
    
    # Build topup text
    topup_text = """💳 အကောင့်ငွေဖြည့်ရန်

သင့်ငွေဖြည့်မှုပမာဏကို ရွေးချယ်ပါ:

သင့်ငွေဖြည့်မှုကို ဆက်လက်လုပ်ဆောင်ရန် အောက်ပါခလုတ်များကို နှိပ်ပါ:"""
    

    
    # Create inline keyboard for top-up options
    markup = InlineKeyboardMarkup()
    for credits, mmk_price in topup_options:
        button = InlineKeyboardButton(f"💎 {credits} Credits - {mmk_price:,} MMK", 
                                    callback_data=f'topup_{credits}')
        markup.add(button)
    
    bot.send_message(message.chat.id, topup_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🆕 New Order")
def handle_new_order(message):
    """Handle New Order button"""
    order_text = """
🆕 **Create New Order**

**Available Services:**
• VPN Keys (1 month) - $5.00
• VPN Keys (3 months) - $12.00
• VPN Keys (6 months) - $20.00
• VPN Keys (12 months) - $35.00

**Order Process:**
1. Select service type
2. Choose quantity
3. Review order details
4. Complete payment
5. Receive your VPN keys

Click below to start your order:
    """
    
    # Create inline keyboard for order options
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("1 Month - $5.00", callback_data='order_1month')
    button2 = InlineKeyboardButton("3 Months - $12.00", callback_data='order_3months')
    button3 = InlineKeyboardButton("6 Months - $20.00", callback_data='order_6months')
    button4 = InlineKeyboardButton("12 Months - $35.00", callback_data='order_12months')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    markup.add(button4)
    
    bot.send_message(message.chat.id, order_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔐 Buy VPN Keys")
def handle_buy_vpn_keys(message):
    """Handle Buy VPN Keys button"""
    vpn_text = """
🔐 **VPN Keys Store**

**Premium VPN Services:**
• High-speed servers worldwide
• 256-bit encryption
• No-logs policy
• 24/7 customer support

**Available Packages:**
• Single Key (1 month) - $5.00
• Family Pack (3 keys, 1 month) - $12.00
• Business Pack (10 keys, 1 month) - $35.00

**Features:**
✅ Unlimited bandwidth
✅ Multiple device support
✅ Global server network
✅ 30-day money-back guarantee

Choose your package below:
    """
    
    # Create inline keyboard for VPN packages
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("Single Key - $5.00", callback_data='vpn_single')
    button2 = InlineKeyboardButton("Family Pack - $12.00", callback_data='vpn_family')
    button3 = InlineKeyboardButton("Business Pack - $35.00", callback_data='vpn_business')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    
    bot.send_message(message.chat.id, vpn_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📋 Order Lists")
def handle_order_lists(message):
    """Handle Order Lists button"""
    orders_text = f"""
📋 **Your Order History**

**Recent Orders:**
• Order #12345 - VPN Key (1 month) - $5.00 - ✅ Completed
• Order #12344 - VPN Key (3 months) - $12.00 - ✅ Completed
• Order #12343 - Top-up - $25.00 - ✅ Completed

**Active Orders:**
• Order #12346 - VPN Key (6 months) - $20.00 - 🔄 Processing

**Order Statistics:**
• Total Orders: 4
• Total Spent: $62.00
• Active VPN Keys: 2

Click below to view detailed order information:
    """
    
    # Create inline keyboard for order actions
    markup = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("View All Orders", callback_data='view_all_orders')
    button2 = InlineKeyboardButton("Download Keys", callback_data='download_keys')
    button3 = InlineKeyboardButton("Order Support", callback_data='order_support')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    
    bot.send_message(message.chat.id, orders_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "VPN Key ဝယ်ရန်")
def handle_buy_plans(message):
    """Handle Buy Plans button"""
    # Ensure user exists
    ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get active plans
    plans = get_active_plans()
    
    if not plans:
        bot.send_message(message.chat.id, "❌ လက်ရှိတွင် ပက်ကေ့ချ်များ မရှိပါ။ ကျေးဇူးပြု၍ ဝန်ဆောင်မှုကို ဆက်သွယ်ပါ။", 
                        reply_markup=create_main_menu())
        return
    
    plans_text = """🛒 **ရရှိနိုင်သော VPN ပက်ကေ့ချ်များ**

ဝယ်ယူရန် ပက်ကေ့ချ်တစ်ခုကို ရွေးချယ်ပါ:"""
    
    # Create inline keyboard for plans
    markup = InlineKeyboardMarkup()
    for plan in plans:
        plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit = plan
        button_text = f"{name} - {credits_required} Credits ({duration_days} days)"
        button = InlineKeyboardButton(button_text, callback_data=f'buy_plan_{plan_id}')
        markup.add(button)
    
    bot.send_message(message.chat.id, plans_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📋 ကျွန်ုပ်၏ပက်ကေ့ချ်")
def handle_my_plans(message):
    """Handle My Plans button"""
    # Ensure user exists
    ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get user's plans
    user_plans = get_user_plans(message.from_user.id)
    
    if not user_plans:
        bot.send_message(message.chat.id, "📋 **ကျွန်ုပ်၏ပက်ကေ့ချ်များ**\n\nသင်သည် မည်သည့်ပက်ကေ့ချ်ကိုမှ မဝယ်ယူရသေးပါ။\n\nရရှိနိုင်သောပက်ကေ့ချ်များကို ကြည့်ရှုရန် 'VPN Key ဝယ်ရန်' ကို အသုံးပြုပါ။", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
        return
    
    plans_text = """📋 **ကျွန်ုပ်၏ဝယ်ယူထားသော ပက်ကေ့ချ်များ**

သင့်လုပ်ဆောင်နေသော ပက်ကေ့ချ်များ:"""
    
    for plan in user_plans:
        plan_id, name, description, key_value, purchase_date, expiry_date, status, api_response = plan
        
        plans_text += f"\n\n**{name}**"
        if description:
            plans_text += f"\n{description}"
        
        # Check if this is a QITO plan with API response
        if api_response and 'QITO' in name:
            try:
                api_data = json.loads(api_response)
                username = api_data.get('username', 'N/A')
                password = api_data.get('password', 'N/A')
                plans_text += f"\n🗝 QITO Username: `{username}`"
                plans_text += f"\n🗝 QITO Password: `{password}`"
            except:
                # Fallback to key_value if API response parsing fails
                if key_value:
                    plans_text += f"\n🔑 VPN Key: `{key_value}`"
        else:
            # Regular VPN plan
            if key_value:
                plans_text += f"\n🔑 VPN Key: `{key_value}`"
        
        plans_text += f"\n📅 Purchased: {purchase_date[:10]}"
        plans_text += f"\n⏰ Expires: {expiry_date[:10] if expiry_date else 'Never'}"
        plans_text += f"\n📊 Status: {status.title()}"
    
    bot.send_message(message.chat.id, plans_text, parse_mode='Markdown', reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: message.text == "🗝 QITO Key")
def handle_qito_key(message):
    """Handle QITO Key button"""
    print("=" * 50)
    print(f"🔔 QITO Key button pressed!")
    print(f"👤 User: {message.from_user.first_name} {message.from_user.last_name or ''}")
    print(f"🆔 User ID: {message.from_user.id}")
    print(f"📱 Username: @{message.from_user.username or 'Not set'}")
    print(f"💬 Chat ID: {message.chat.id}")
    print("=" * 50)
    # Ensure user exists
    ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get QITO plans (plans with "QITO" in the name)
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, 
               COALESCE(p.device_limit, 1) as device_limit
        FROM plans p
        WHERE p.name LIKE '%QITO%' AND p.is_active = 1
        ORDER BY p.plan_id_number
    ''')
    qito_plans = cursor.fetchall()
    conn.close()
    
    if not qito_plans:
        bot.send_message(message.chat.id, "❌ လက်ရှိတွင် QITO ပက်ကေ့ချ်များ မရှိပါ။ ကျေးဇူးပြု၍ ဝန်ဆောင်မှုကို ဆက်သွယ်ပါ။", 
                        reply_markup=create_main_menu())
        return
    
    qito_text = """🗝 **QITO ပက်ကေ့ချ်များ**

QITO ပက်ကေ့ချ်များကို ကြည့်ရှုပြီး ရွေးချယ်ပါ:"""
    
    # Create inline keyboard for QITO plans
    print(f"📋 Creating QITO plan buttons for {len(qito_plans)} plans...")
    markup = InlineKeyboardMarkup()
    for plan in qito_plans:
        plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit, device_limit_alias = plan
        button_text = f"{name} - {credits_required} Credits ({duration_days} days, {device_limit_alias} devices)"
        button = InlineKeyboardButton(button_text, callback_data=f'qito_plan_{plan_id}')
        markup.add(button)
        print(f"  ✅ Added: {button_text}")
        print(f"     🔗 Callback: qito_plan_{plan_id}")
    
    print(f"📤 Sending QITO plans message to user {message.from_user.id}")
    bot.send_message(message.chat.id, qito_text, parse_mode='Markdown', reply_markup=markup)
    print("✅ QITO plans message sent successfully!")

@bot.message_handler(func=lambda message: message.text == "📞 ဆက်သွယ်ရန်")
def handle_contact(message):
    """Handle Contact button"""
    try:
        print(f"Contact button pressed by user {message.from_user.id}")
        
        # Get dynamic contact information from database
        contacts = get_active_contact_config()
        print(f"Retrieved {len(contacts)} active contacts")
        
        # Build contact text dynamically
        contact_text = "📞 **ဆက်သွယ်ရန်နှင့် ဝန်ဆောင်မှု**\n\n"
        
        # Create a dictionary for easy lookup
        contact_dict = {contact_type: contact_value for contact_type, contact_value in contacts}
        
        # Add contact information based on what's configured
        if 'telegram' in contact_dict:
            contact_text += f"**Telegram ဝန်ဆောင်မှု:**\n• {contact_dict['telegram']}\n\n"
        
        if 'telegram_admin' in contact_dict:
            contact_text += f"**အက်မင်ဆက်သွယ်ရန်:**\n• {contact_dict['telegram_admin']}\n\n"
        
        if 'email' in contact_dict:
            contact_text += f"**အီးမေးလ်:**\n• {contact_dict['email']}\n\n"
        
        if 'phone' in contact_dict:
            contact_text += f"**ဖုန်း:**\n• {contact_dict['phone']}\n\n"
        
        if 'website' in contact_dict:
            contact_text += f"**ဝဘ်ဆိုက်:**\n• {contact_dict['website']}\n\n"
        
        if 'response_time' in contact_dict:
            contact_text += f"**တုံ့ပြန်ချိန်:**\n• {contact_dict['response_time']}\n\n"
        
        if 'business_hours' in contact_dict:
            contact_text += f"**လုပ်ငန်းလုပ်ချိန်:**\n• {contact_dict['business_hours']}\n\n"
        
        print(f"Sending contact message to user {message.from_user.id}")
        bot.send_message(message.chat.id, contact_text, parse_mode='Markdown', reply_markup=create_main_menu())
        print("Contact message sent successfully")
        
    except Exception as e:
        print(f"Error in handle_contact: {e}")
        import traceback
        traceback.print_exc()
        
        # Send fallback message
        fallback_text = "📞 **ဆက်သွယ်ရန်နှင့် ဝန်ဆောင်မှု**\n\nဆက်သွယ်ရန်အချက်အလက်များကို ဖွင့်ရာတွင် ပြဿနာတစ်ခုရှိပါတယ်။ ကျေးဇူးပြု၍ နောက်မှ ပြန်လည်ကြိုးစားပါ သို့မဟုတ် ဝန်ဆောင်မှုကို တိုက်ရိုက်ဆက်သွယ်ပါ။"
        bot.send_message(message.chat.id, fallback_text, reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: message.text == "📱 Download APK")
def handle_download_apk(message):
    """Handle Download APK button"""
    import os
    
    apk_file_path = "apk_files/latest.apk"
    
    if os.path.exists(apk_file_path):
        try:
            # Get file size
            file_size = os.path.getsize(apk_file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Check if file is too large for Telegram (100MB limit)
            if file_size_mb > 100:
                large_file_text = f"""📱 Download APK

APK ဖိုင်ရှိပါသည် (Size: {file_size_mb:.1f} MB)

သို့သော် ဖိုင်အရွယ်အစားကြီးလွန်းသောကြောင့် Telegram မှ တိုက်ရိုက်ပို့ပေးနိုင်မည်မဟုတ်ပါ။

အက်မင်မှ ဖိုင်ကို ပို့ပေးရန် ဆက်သွယ်ပါ:
• Telegram: @admin_username
• သို့မဟုတ် ဝဘ်ဆိုက်မှ ဒေါင်းလုဒ်လုပ်ပါ

ကျေးဇူးပြု၍ နားလည်မှုရှိပါ။"""
                
                bot.send_message(message.chat.id, large_file_text, reply_markup=create_main_menu())
                return
            
            # Send file with timeout handling
            with open(apk_file_path, 'rb') as apk_file:
                # Send with longer timeout
                bot.send_document(
                    message.chat.id, 
                    apk_file, 
                    caption="📱 VPN APK File\n\nဤဖိုင်ကို သင့်ဖုန်းတွင် ထည့်သွင်းပါ။",
                    timeout=60  # 60 seconds timeout
                )
                
        except Exception as e:
            error_message = f"""❌ APK ဖိုင်ကို ပို့ပေးရာတွင် ပြဿနာရှိပါသည်

Error: {str(e)}

ဖြစ်နိုင်သော အကြောင်းရင်းများ:
• ဖိုင်အရွယ်အစားကြီးလွန်းခြင်း
• ကွန်ယက်ချိတ်ဆက်မှု ပြဿနာ
• Telegram ဝန်ဆောင်မှု ပြဿနာ

အက်မင်မှ ဖိုင်ကို တိုက်ရိုက်ပို့ပေးရန် ဆက်သွယ်ပါ။"""
            
            bot.send_message(message.chat.id, error_message, reply_markup=create_main_menu())
    else:
        no_apk_text = """📱 Download APK

လက်ရှိတွင် APK ဖိုင်မရှိပါ။

အက်မင်မှ APK ဖိုင်ကို ပို့ပေးပါက ဤနေရာတွင် ရရှိနိုင်မည်။

ကျေးဇူးပြု၍ နောက်ပိုင်းတွင် ပြန်လည်စမ်းကြည့်ပါ။"""
        
        bot.send_message(message.chat.id, no_apk_text, reply_markup=create_main_menu())

# Handle inline keyboard callbacks
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle all callback queries from inline keyboards"""
    
    # Top-up callbacks
    if call.data.startswith('topup_'):
        credits = call.data.split('_')[1]
        
        # Get the MMK price from database
        topup_options = get_topup_options()
        mmk_price = None
        for option_credits, option_mmk in topup_options:
            if str(option_credits) == credits:
                mmk_price = option_mmk
                break
        
        if mmk_price:
            bot.answer_callback_query(call.id, f"Top-up {credits} credits selected!")
            
            # Delete the original topup message
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                print(f"Could not delete message: {e}")
            
            # Create pending payment record
            payment_id = create_pending_payment(call.from_user.id, int(credits), mmk_price)
            
            # Get payment methods
            payment_methods = get_payment_methods()
            
            payment_details = f"""💳 ငွေပေးချေမှုအသေးစိတ်

ငွေဖြည့်ပမာဏ: {credits} Credits
ဈေးနှုန်း: {mmk_price:,} ကျပ်

💳 ရရှိနိုင်သောငွေပေးချေမှုနည်းလမ်းများ:
"""
            for name, description in payment_methods:
                if description:
                    payment_details += f"• **{name}**\n  {description}\n"
                else:
                    payment_details += f"• **{name}**\n"
            
            payment_details += f"""
ငွေပေးချေရန် အောက်ပါအတိုင်းလုပ်ဆောင်ပါ
1. ငွေလွှဲထားသော screenshot ပို့ပေးထားပါ
2. အက်မင်အတည်ပြုချက်ကို စောင့်ပါ(Admin ဘက်မှအတည်ပြုပြီးသည်နှင့် Credit များထည့်သွင်းပေးထားပါမည်)

ငွေပေးချေမှု ID: #{payment_id}"""
            
            bot.send_message(call.message.chat.id, payment_details, reply_markup=create_main_menu())
        else:
            bot.answer_callback_query(call.id, "Topup option not found!")
            bot.send_message(call.message.chat.id, "❌ Topup option not available. Please try again.", 
                            reply_markup=create_main_menu())
    
    # Order callbacks
    elif call.data.startswith('order_'):
        period = call.data.split('_')[1]
        prices = {'1month': '$5.00', '3months': '$12.00', '6months': '$20.00', '12months': '$35.00'}
        price = prices.get(period, 'N/A')
        bot.answer_callback_query(call.id, f"Order {period} selected!")
        bot.send_message(call.message.chat.id, f"🆕 **New Order: {period.title()}**\n\nPrice: {price}\n\nProcessing your order...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    # VPN package callbacks
    elif call.data.startswith('vpn_'):
        package = call.data.split('_')[1]
        packages = {'single': 'Single Key - $5.00', 'family': 'Family Pack - $12.00', 'business': 'Business Pack - $35.00'}
        package_name = packages.get(package, 'Unknown Package')
        bot.answer_callback_query(call.id, f"VPN package selected!")
        bot.send_message(call.message.chat.id, f"🔐 **VPN Package Selected**\n\n{package_name}\n\nProcessing your purchase...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    # Order list callbacks
    elif call.data == 'view_all_orders':
        bot.answer_callback_query(call.id, "Loading all orders...")
        bot.send_message(call.message.chat.id, "📋 **All Orders**\n\nLoading your complete order history...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    elif call.data == 'download_keys':
        bot.answer_callback_query(call.id, "Preparing download...")
        bot.send_message(call.message.chat.id, "🔐 **VPN Keys Download**\n\nPreparing your VPN keys for download...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    elif call.data == 'order_support':
        bot.answer_callback_query(call.id, "Connecting to support...")
        bot.send_message(call.message.chat.id, "📞 **Order Support**\n\nConnecting you with our order support team...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    # Support callbacks
    elif call.data.startswith('support_'):
        support_type = call.data.split('_')[1]
        support_types = {'technical': 'Technical Support', 'billing': 'Billing Support', 'account': 'Account Support', 'general': 'General Inquiry'}
        support_name = support_types.get(support_type, 'Support')
        bot.answer_callback_query(call.id, f"{support_name} selected!")
        bot.send_message(call.message.chat.id, f"📞 **{support_name}**\n\nConnecting you with our {support_name.lower()} team...", 
                        parse_mode='Markdown', reply_markup=create_main_menu())
    
    # Legacy callbacks (keeping for compatibility)
    elif call.data == "option_a_selected":
        bot.answer_callback_query(call.id, "Option A selected!")
        bot.send_message(call.message.chat.id, "✅ You selected Option A! This is a callback button example.", 
                        reply_markup=create_inline_menu())
    
    elif call.data == "inline_random":
        import random
        random_num = random.randint(1, 100)
        bot.answer_callback_query(call.id, f"Generated: {random_num}")
        bot.send_message(call.message.chat.id, f"🎲 Your random number is: **{random_num}**", 
                        parse_mode='Markdown', reply_markup=create_inline_menu())
    
    elif call.data == "get_user_info":
        info_text = f"""
📊 **Your Information:**

• Name: {call.from_user.first_name} {call.from_user.last_name or ''}
• Username: @{call.from_user.username or 'Not set'}
• User ID: {call.from_user.id}
• Language: {call.from_user.language_code or 'Not set'}
        """
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, info_text, parse_mode='Markdown', 
                        reply_markup=create_info_inline_menu())
    
    elif call.data == "back_to_main":
        welcome_text = f"Welcome back, {call.from_user.first_name}! 👋\n\nChoose an option below:"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, welcome_text, reply_markup=create_inline_menu())
    
    # Admin approval callbacks
    elif call.data.startswith('admin_approve_'):
        print(f"Admin approval attempt by user {call.from_user.id}, expected admin {ADMIN_TELEGRAM_ID}")
        
        if str(call.from_user.id) == str(ADMIN_TELEGRAM_ID):
            payment_id = call.data.split('_')[2]
            print(f"Processing approval for payment ID: {payment_id}")
            
            payment = get_pending_payment(payment_id)
            print(f"Payment data: {payment}")
            
            if payment:
                # payment structure: (id, user_id, credits, mmk_price, payment_proof_file_id, status, created_at, processed_at)
                payment_status = payment[5] if len(payment) > 5 else 'unknown'
                print(f"Payment status: {payment_status}")
                
                if payment_status == 'pending':
                    # Update payment status
                    update_payment_status(payment_id, 'approved')
                    
                    # Add balance to user
                    add_user_balance(payment[1], payment[2])  # user_id, credits
                    
                    # Notify user
                    user_message = f"""✅ Payment Approved!

✅  Credits ထပ်ပေါင်းထည့်ပြီးပါပြီဗျ

Payment ID: #{payment_id}
Credit Added: {payment[2]} Credits
Amount Paid: {payment[3]:,} MMK

👤ကျွန်ုပ်၏ Credit ကိုနှိပ်၍ Credit လက်ကျန်စစ်ဆေးနိုင်ပါသည်

❤️ဝယ်ယူအားပေးမှုအတွက် ကျေးဇူးပါဗျ"""
                    
                    bot.send_message(payment[1], user_message, reply_markup=create_main_menu())
                    
                    # Notify admin
                    bot.answer_callback_query(call.id, f"Payment #{payment_id} approved!")
                    bot.send_message(call.from_user.id, f"✅ Payment #{payment_id} has been approved and {payment[2]} credits added to user's account.")
                else:
                    bot.answer_callback_query(call.id, f"Payment already processed! Status: {payment_status}")
            else:
                bot.answer_callback_query(call.id, "Payment not found!")
                print(f"Payment with ID {payment_id} not found in database")
        else:
            bot.answer_callback_query(call.id, "Unauthorized!")
            print(f"Unauthorized access attempt by user {call.from_user.id}")
    
    elif call.data.startswith('admin_deny_'):
        print(f"Admin denial attempt by user {call.from_user.id}, expected admin {ADMIN_TELEGRAM_ID}")
        
        if str(call.from_user.id) == str(ADMIN_TELEGRAM_ID):
            payment_id = call.data.split('_')[2]
            print(f"Processing denial for payment ID: {payment_id}")
            
            payment = get_pending_payment(payment_id)
            print(f"Payment data: {payment}")
            
            if payment:
                # payment structure: (id, user_id, credits, mmk_price, payment_proof_file_id, status, created_at, processed_at)
                payment_status = payment[5] if len(payment) > 5 else 'unknown'
                print(f"Payment status: {payment_status}")
                
                if payment_status == 'pending':
                    # Update payment status
                    update_payment_status(payment_id, 'denied')
                    
                    # Notify user
                    user_message = f"""❌ Payment Denied

Payment ID: #{payment_id}
Amount: {payment[2]} Credits ({payment[3]:,} MMK)

Your payment has been denied. Please contact support if you believe this is an error.

You can try making a new payment with a clearer payment proof."""
                    
                    bot.send_message(payment[1], user_message, reply_markup=create_main_menu())
                    
                    # Notify admin
                    bot.answer_callback_query(call.id, f"Payment #{payment_id} denied!")
                    bot.send_message(call.from_user.id, f"❌ Payment #{payment_id} has been denied.")
                else:
                    bot.answer_callback_query(call.id, f"Payment already processed! Status: {payment_status}")
            else:
                bot.answer_callback_query(call.id, "Payment not found!")
                print(f"Payment with ID {payment_id} not found in database")
        else:
            bot.answer_callback_query(call.id, "Unauthorized!")
            print(f"Unauthorized access attempt by user {call.from_user.id}")
    
    # Plan purchase callbacks
    elif call.data.startswith('buy_plan_'):
        plan_id = call.data.split('_')[2]
        plan = get_plan(plan_id)
        
        if plan:
            plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit = plan
            
            # Check if user has enough balance
            user_balance = get_user_balance(call.from_user.id)
            user_credits = int(user_balance * 100)  # Convert to credits
            
            if user_credits >= credits_required:
                # Check if keys are available
                available_keys = get_available_keys(plan_id)
                
                if available_keys:
                    # Delete the original plans message
                    try:
                        bot.delete_message(call.message.chat.id, call.message.message_id)
                    except Exception as e:
                        print(f"Could not delete message: {e}")
                    
                    # Show confirmation dialog
                    confirmation_message = f"""🛒 **Key ဝယ်ယူမှု အတည်ပြုခြင်း!**

• ပက်ကေ့ချ် ID: {plan_id_number}
• Key အမျိုးအစား : {name}
• ဖော်ပြချက်     : {description or 'ဖော်ပြချက်မရှိ'}
• သက်တမ်း      : {duration_days} ရက်
• ကုန်ကျစရိတ်: {credits_required} Credits

**သင့်အကောင့်:**
• လက်ကျန် Credit : {user_credits} Credits

Key Avaliable: {len(available_keys)} Keys

ကျေးဇူးပြု၍ သင့်ဝယ်ယူမှုကို အတည်ပြုပါ:"""
                    
                    # Create confirmation keyboard
                    confirmation_keyboard = InlineKeyboardMarkup()
                    confirm_btn = InlineKeyboardButton("✅ ဝယ်ယူအတည်ပြုပါ", callback_data=f'confirm_purchase_{plan_id}')
                    cancel_btn = InlineKeyboardButton("❌ ပယ်ဖျက်ပါ", callback_data='cancel_purchase')
                    confirmation_keyboard.row(confirm_btn, cancel_btn)
                    
                    bot.answer_callback_query(call.id, "ကျေးဇူးပြု၍ သင့်ဝယ်ယူမှုကို အတည်ပြုပါ")
                    bot.send_message(call.message.chat.id, confirmation_message, 
                                   parse_mode='Markdown', reply_markup=confirmation_keyboard)
                else:
                    bot.answer_callback_query(call.id, "No keys available!")
                    bot.send_message(call.message.chat.id, f"❌ Sorry, no VPN keys are available for {name} at the moment. Please try again later.", 
                                   reply_markup=create_main_menu())
            else:
                bot.answer_callback_query(call.id, "Insufficient balance!")
                bot.send_message(call.message.chat.id, f"❌ Insufficient balance!\n\nYou need {credits_required} credits but only have {user_credits} credits.\n\nUse '💳 Topup' to add more credits.", 
                               reply_markup=create_main_menu())
        else:
            bot.answer_callback_query(call.id, "Plan not found!")
            bot.send_message(call.message.chat.id, "❌ Plan not found. Please try again.", 
                           reply_markup=create_main_menu())
    
    # Plan purchase confirmation callbacks
    elif call.data.startswith('confirm_purchase_'):
        plan_id = call.data.split('_')[2]
        plan = get_plan(plan_id)
        
        if plan:
            plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit = plan
            
            # Double-check balance and key availability
            user_balance = get_user_balance(call.from_user.id)
            user_credits = int(user_balance * 100)
            available_keys = get_available_keys(plan_id)
            
            if user_credits >= credits_required and available_keys:
                # Assign key to user
                vpn_key = assign_key_to_user(plan_id, call.from_user.id)
                
                if vpn_key:
                    # Deduct credits from user balance
                    add_user_balance(call.from_user.id, -credits_required)
                    
                    # Delete the original confirmation message
                    try:
                        bot.delete_message(call.message.chat.id, call.message.message_id)
                    except Exception as e:
                        print(f"Could not delete message: {e}")
                    
                    # Notify user
                    success_message = f"""✅ **Key ဝယ်ယူမှု အောင်မြင်ပါသည်!!**

**ပက်ကေ့ချ် ID:** {plan_id_number}
**Key အမျိုးအစား :** {name}
**သက်တမ်း:** {duration_days} ရက်
**ကုန်ကျစရိတ်:** {credits_required} Credits
**VPN Key ⬇️** 

`{vpn_key}`"""
                    
                    bot.answer_callback_query(call.id, "Key ဝယ်ယူမှု အောင်မြင်ပါသည်!!")
                    bot.send_message(call.message.chat.id, success_message, 
                                   parse_mode='Markdown', reply_markup=create_main_menu())
                    
                    # Notify admin
                    if ADMIN_TELEGRAM_ID:
                        admin_message = f"""🔔 **New Plan Purchase**

User: {call.from_user.first_name} {call.from_user.last_name or ''}
Username: @{call.from_user.username or 'Not set'}
User ID: {call.from_user.id}
Plan ID: {plan_id_number}
Plan: {name}
VPN Key: {vpn_key}
Credits Used: {credits_required}"""
                        
                        bot.send_message(ADMIN_TELEGRAM_ID, admin_message)
                    
                    # Check for low keys after successful purchase
                    check_and_notify_low_keys()
                else:
                    bot.answer_callback_query(call.id, "Error assigning VPN key!")
                    bot.send_message(call.message.chat.id, "❌ Error processing your purchase. Please try again.", 
                                   reply_markup=create_main_menu())
            else:
                bot.answer_callback_query(call.id, "Plan no longer available!")
                bot.send_message(call.message.chat.id, "❌ Sorry, this plan is no longer available or you don't have enough credits. Please try again.", 
                               reply_markup=create_main_menu())
        else:
            bot.answer_callback_query(call.id, "Plan not found!")
            bot.send_message(call.message.chat.id, "❌ Plan not found. Please try again.", 
                           reply_markup=create_main_menu())
    
    # Cancel purchase callback
    elif call.data == 'cancel_purchase':
        bot.answer_callback_query(call.id, "ဝယ်ယူမှုပယ်ဖျက်ပြီး")
        bot.send_message(call.message.chat.id, "❌ ဝယ်ယူမှုပယ်ဖျက်ပြီးပါပြီ။ မည်သည့်အချိန်တွင်မဆို အခြားပက်ကေ့ချ်များကို ကြည့်ရှုနိုင်ပါတယ်။", 
                       reply_markup=create_main_menu())
    
    # QITO plan callbacks
    elif call.data.startswith('qito_plan_'):
        print("=" * 60)
        print(f"🎯 QITO PLAN CALLBACK RECEIVED!")
        print(f"📞 Callback Data: {call.data}")
        print(f"👤 User: {call.from_user.first_name} {call.from_user.last_name or ''}")
        print(f"🆔 User ID: {call.from_user.id}")
        print(f"📱 Username: @{call.from_user.username or 'Not set'}")
        print(f"💬 Chat ID: {call.message.chat.id}")
        print(f"📝 Message ID: {call.message.message_id}")
        
        plan_id = call.data.split('_')[2]
        print(f"🔍 Extracted Plan ID: {plan_id}")
        
        plan = get_plan(plan_id)
        if plan:
            print(f"✅ Plan Found: {plan[2]} (ID: {plan[0]})")
            print(f"💰 Credits Required: {plan[4]}")
            print(f"⏰ Duration: {plan[5]} days")
        else:
            print(f"❌ Plan NOT Found for ID: {plan_id}")
        print("=" * 60)
        
        if plan:
            plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit = plan
            
            print(f"🔧 Device Limit: {device_limit}")
            
            # Check if user has enough balance
            user_balance = get_user_balance(call.from_user.id)
            user_credits = int(user_balance * 100)  # Convert to credits
            
            print(f"💰 User Balance Check:")
            print(f"   💵 User Balance: {user_balance}")
            print(f"   🪙 User Credits: {user_credits}")
            print(f"   💰 Required Credits: {credits_required}")
            print(f"   ✅ Sufficient Balance: {user_credits >= credits_required}")
            
            if user_credits >= credits_required:
                # Delete the original QITO plans message
                print(f"🗑️ Deleting original QITO plans message...")
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                    print(f"✅ Message deleted successfully!")
                except Exception as e:
                    print(f"❌ Could not delete message: {e}")
                
                # Show QITO confirmation dialog
                print(f"📝 Showing QITO confirmation dialog...")
                confirmation_message = f"""🗝 **QITO ပက်ကေ့ချ် ဝယ်ယူမှု အတည်ပြုခြင်း!**

• ပက်ကေ့ချ် ID: {plan_id_number}
• QITO ပက်ကေ့ချ် : {name}
• ဖော်ပြချက်     : {description or 'ဖော်ပြချက်မရှိ'}
• သက်တမ်း      : {duration_days} ရက်
• ကုန်ကျစရိတ်: {credits_required} Credits
• စက်အရေအတွက်: {device_limit} စက်

**သင့်အကောင့်:**
• လက်ကျန် Credit : {user_credits} Credits

QITO ပက်ကေ့ချ်သည် subscription-based ဖြစ်ပြီး သီးခြား key မလိုအပ်ပါ။

ကျေးဇူးပြု၍ သင့်ဝယ်ယူမှုကို အတည်ပြုပါ:"""
                
                # Create confirmation keyboard
                confirmation_keyboard = InlineKeyboardMarkup()
                confirm_btn = InlineKeyboardButton("✅ QITO ပက်ကေ့ချ် ဝယ်ယူအတည်ပြုပါ", callback_data=f'confirm_qito_purchase_{plan_id}')
                cancel_btn = InlineKeyboardButton("❌ ပယ်ဖျက်ပါ", callback_data='cancel_qito_purchase')
                confirmation_keyboard.row(confirm_btn, cancel_btn)
                
                print(f"📤 Sending confirmation message...")
                bot.answer_callback_query(call.id, "ကျေးဇူးပြု၍ သင့်ဝယ်ယူမှုကို အတည်ပြုပါ")
                bot.send_message(call.message.chat.id, confirmation_message, 
                               parse_mode='Markdown', reply_markup=confirmation_keyboard)
                print(f"✅ QITO confirmation message sent successfully!")
            else:
                bot.answer_callback_query(call.id, "Insufficient balance!")
                bot.send_message(call.message.chat.id, f"❌ Insufficient balance!\n\nYou need {credits_required} credits but only have {user_credits} credits.\n\nUse '💳 ငွေဖြည့်' to add more credits.", 
                               reply_markup=create_main_menu())
        else:
            bot.answer_callback_query(call.id, "QITO plan not found!")
            bot.send_message(call.message.chat.id, "❌ QITO plan not found. Please try again.", 
                           reply_markup=create_main_menu())
    
    # QITO purchase confirmation callbacks
    elif call.data.startswith('confirm_qito_purchase_'):
        plan_id = call.data.split('_')[3]
        plan = get_plan(plan_id)
        
        if plan:
            plan_id, plan_id_number, name, description, credits_required, duration_days, is_active, created_at, updated_at, device_limit = plan
            
            # Get device limit from database
            from database import get_db_connection_with_retry
            conn = get_db_connection_with_retry()
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(device_limit, 1) FROM plans WHERE id = ?', (plan_id,))
            device_limit = cursor.fetchone()[0]
            conn.close()
            
            # Double-check balance
            user_balance = get_user_balance(call.from_user.id)
            user_credits = int(user_balance * 100)
            
            if user_credits >= credits_required:
                # Create QITO user via API
                api_response = create_qito_user_api(device_limit, duration_days)
                
                if api_response:
                    # API call successful, store the response data
                    from datetime import datetime, timedelta
                    purchase_date = datetime.now()
                    expiry_date = purchase_date + timedelta(days=duration_days)
                    
                    # Create user plan record with API response data
                    print("🔧 Creating database connection for user plan insert...")
                    conn2 = get_db_connection_with_retry()
                    print("✅ Database connection created successfully")
                    cursor2 = conn2.cursor()
                    print("✅ Cursor created successfully")
                    print("🔧 Executing INSERT query...")
                    cursor2.execute('''
                        INSERT INTO user_plans (user_id, plan_id, purchase_date, expiry_date, status, vpn_key, api_response)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (call.from_user.id, plan_id, purchase_date, expiry_date, 'active', 
                          f"{api_response.get('username', '')}|{api_response.get('password', '')}", 
                          json.dumps(api_response)))
                    print("✅ INSERT query executed successfully")
                    print("🔧 Committing transaction...")
                    conn2.commit()
                    print("✅ Transaction committed successfully")
                    print("🔧 Closing database connection...")
                    conn2.close()
                    print("✅ Database connection closed successfully")
                    
                    # Deduct credits from user balance
                    add_user_balance(call.from_user.id, -credits_required)
                    
                    # Delete the original confirmation message
                    try:
                        bot.delete_message(call.message.chat.id, call.message.message_id)
                    except Exception as e:
                        print(f"Could not delete message: {e}")
                    
                    # Notify user with credentials
                    success_message = f"""✅ **QITO ပက်ကေ့ချ် ဝယ်ယူမှု အောင်မြင်ပါသည်!!**

**ပက်ကေ့ချ် ID:** {plan_id_number}
**QITO ပက်ကေ့ချ် :** {name}
**သက်တမ်း:** {duration_days} ရက်
**ကုန်ကျစရိတ်:** {credits_required} Credits
**စက်အရေအတွက်:** {device_limit} စက်
**သက်တမ်းကုန်ဆုံးရက်:** {expiry_date.strftime('%Y-%m-%d')}

**QITO အကောင့်အသေးစိတ် ⬇️**

**Username:** `{api_response.get('username', 'N/A')}`
**Password:** `{api_response.get('password', 'N/A')}`

**QITO ပက်ကေ့ချ်အသုံးပြုနည်း:**
• QITO ပက်ကေ့ချ်သည် subscription-based ဖြစ်ပါသည်
• သင့်အကောင့်နှင့် ချိတ်ဆက်ပြီး အသုံးပြုနိုင်ပါသည်
• စက်အရေအတွက်: {device_limit} စက် အထိ အသုံးပြုနိုင်ပါသည်

**အကူအညီလိုအပ်ပါက ဆက်သွယ်ပါ:**
📞 ဆက်သွယ်ရန် ခလုတ်ကို နှိပ်ပါ"""
                    
                    bot.answer_callback_query(call.id, "QITO ပက်ကေ့ချ် ဝယ်ယူမှု အောင်မြင်ပါသည်!!")
                    bot.send_message(call.message.chat.id, success_message, 
                                   parse_mode='Markdown', reply_markup=create_main_menu())
                    
                    # Notify admin
                    if ADMIN_TELEGRAM_ID:
                        admin_message = f"""🔔 **New QITO Plan Purchase**

User: {call.from_user.first_name} {call.from_user.last_name or ''}
Username: @{call.from_user.username or 'Not set'}
User ID: {call.from_user.id}
Plan ID: {plan_id_number}
Plan: {name}
Device Limit: {device_limit} devices
Duration: {duration_days} days
Expiry Date: {expiry_date.strftime('%Y-%m-%d')}
Credits Used: {credits_required}
QITO Username: {api_response.get('username', 'N/A')}
QITO Password: {api_response.get('password', 'N/A')}"""
                        
                        bot.send_message(ADMIN_TELEGRAM_ID, admin_message)
                else:
                    # API call failed
                    conn.close()
                    bot.answer_callback_query(call.id, "API Error!")
                    bot.send_message(call.message.chat.id, "❌ QITO service is temporarily unavailable. Please try again later.", 
                                   reply_markup=create_main_menu())
            else:
                conn.close()
                bot.answer_callback_query(call.id, "Insufficient balance!")
                bot.send_message(call.message.chat.id, "❌ Sorry, you don't have enough credits. Please top up your account.", 
                               reply_markup=create_main_menu())
        else:
            bot.answer_callback_query(call.id, "QITO plan not found!")
            bot.send_message(call.message.chat.id, "❌ QITO plan not found. Please try again.", 
                           reply_markup=create_main_menu())
    
    # Cancel QITO purchase callback
    elif call.data == 'cancel_qito_purchase':
        bot.answer_callback_query(call.id, "QITO ဝယ်ယူမှုပယ်ဖျက်ပြီး")
        bot.send_message(call.message.chat.id, "❌ QITO ဝယ်ယူမှုပယ်ဖျက်ပြီးပါပြီ။ မည်သည့်အချိန်တွင်မဆို အခြားပက်ကေ့ချ်များကို ကြည့်ရှုနိုင်ပါတယ်။", 
                       reply_markup=create_main_menu())

@bot.message_handler(content_types=['photo'])
def handle_payment_proof(message):
    """Handle payment proof images"""
    # Ensure user exists
    ensure_user_exists(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get the largest photo
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Get user's latest pending payment
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, credits, mmk_price FROM pending_payments 
        WHERE user_id = ? AND status = 'pending' 
        ORDER BY created_at DESC LIMIT 1
    ''', (message.from_user.id,))
    payment = cursor.fetchone()
    conn.close()
    
    if payment:
        payment_id, credits, mmk_price = payment
        
        # Update payment with file ID
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE pending_payments SET payment_proof_file_id = ? WHERE id = ?', 
                      (file_id, payment_id))
        conn.commit()
        conn.close()
        
        # Notify user
        bot.send_message(message.chat.id, 
                        f"✅ငွေပေးချေမှုအတည်ပြုရန် ခေတ္တစောင့်ဆိုင်းပေးပါ!\n\nPayment ID: #{payment_id}\nထည့်မည့်ပမာဏ: {credits} Credits", 
                        reply_markup=create_main_menu())
        
        # Notify admin
        if ADMIN_TELEGRAM_ID:
            admin_message = f"""🔔 New Payment Proof Received

Payment ID: #{payment_id}
User: {message.from_user.first_name} {message.from_user.last_name or ''}
Username: @{message.from_user.username or 'Not set'}
User ID: {message.from_user.id}
Amount: {credits} Credits ({mmk_price:,} MMK)
Date: {message.date}

Please review the payment proof and approve or deny the payment."""
            
            # Create admin approval keyboard
            admin_keyboard = InlineKeyboardMarkup()
            approve_btn = InlineKeyboardButton("✅ Approve", callback_data=f'admin_approve_{payment_id}')
            deny_btn = InlineKeyboardButton("❌ Deny", callback_data=f'admin_deny_{payment_id}')
            admin_keyboard.row(approve_btn, deny_btn)
            
            print(f"Sending payment proof to admin {ADMIN_TELEGRAM_ID} for payment #{payment_id}")
            
            # Send to admin with photo
            bot.send_photo(ADMIN_TELEGRAM_ID, file_id, caption=admin_message, reply_markup=admin_keyboard)
        else:
            print(f"⚠️ Admin Telegram ID not set! Payment proof received for payment #{payment_id}")
    else:
        bot.send_message(message.chat.id, 
                        "❌ No pending payment found. Please select a topup option first and then send your payment proof.", 
                        reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle all other messages"""
    response_text = f"Hello {message.from_user.first_name}! 👋\n\nI received your message: '{message.text}'\n\nUse /start to see the main menu or /help for available commands."
    
    bot.send_message(message.chat.id, response_text, reply_markup=create_main_menu())

if __name__ == '__main__':
    print("🤖 Starting Telegram Bot...")
    print("Press Ctrl+C to stop the bot")
    
    try:
        bot.infinity_polling(none_stop=True)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
