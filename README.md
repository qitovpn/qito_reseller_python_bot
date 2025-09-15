# QitopyBot - VPN Service Telegram Bot

A comprehensive VPN service Telegram bot built with `pyTelegramBotAPI` featuring user management, payment processing, plan management, and automated VPN key distribution. The bot interface is available in Myanmar language for local users.

## 🚀 Features

- **Telegram Bot Interface**: User-friendly bot with Myanmar language interface and reply keyboards
- **User Management**: Automatic user registration and balance tracking
- **Topup System**: Credit topup with Myanmar Kyat (MMK) pricing
- **Payment Verification**: Complete payment proof system with admin approval
- **Plan Management**: CRUD operations for VPN plans with credit requirements and durations
- **VPN Key Management**: Automated key assignment and tracking for each plan
- **Low Key Monitoring**: Automatic notifications when plans have fewer than 10 available keys
- **Web Admin Panel**: Flask-based admin interface for managing topups, payments, plans, and keys
- **Database Integration**: SQLite database for user, payment, plan, and key management
- **Admin Notifications**: Real-time notifications to admin for payment approvals, plan purchases, and low key alerts

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token provided by BotFather

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file and add your bot token and admin ID:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   ADMIN_TELEGRAM_ID=your_telegram_id_here
   ```

3. Get your Telegram ID:
   - Message @userinfobot on Telegram
   - Copy your ID number
   - Add it to your .env file

### 5. Test Configuration

Test your bot and admin configuration:
```bash
# Test bot connection
python test_bot.py

# Test admin configuration
python test_admin.py

# Test plan and key management system
python test_plan_system.py

# Test low key notification system
python test_low_key_notification.py

# Test contact configuration system
python test_contact_system.py
```

### 6. Run the Bot

Make sure your virtual environment is activated:

```bash
source venv/bin/activate
```

**Option 1: Run Bot Only**
```bash
python bot.py
```

**Option 2: Run Bot + Web Admin Together**
```bash
# Method 1: Threading approach
python run_both.py

# Method 2: Subprocess approach (recommended)
python run_both_simple.py
```

**Option 3: Run Web Admin Only**
```bash
python start_admin.py
```

## 🌐 Web Admin Panel

The project includes a web-based admin panel for managing topup options and payment methods.

### Starting the Admin Panel

```bash
# Install additional dependencies
pip install -r requirements.txt

# Start the admin panel
python start_admin.py
```

The admin panel will be available at: http://localhost:5000

### Admin Panel Features

- **Dashboard**: Overview of users, balances, and system statistics
- **Topup Management**: Add, edit, delete topup options with MMK pricing
- **Payment Methods**: Manage payment methods (KBZ Pay, Wave Money, etc.)
- **Plan Management**: Create, edit, delete VPN plans with credit requirements and durations
- **VPN Key Management**: Add and manage VPN keys for each plan
- **Contact Configuration**: Manage contact information displayed to users (Telegram-focused)
- **User Management**: View all bot users and their balances
- **API Endpoints**: REST API for bot integration

### Admin Panel URLs

- Dashboard: http://localhost:5000
- Topup Management: http://localhost:5000/topup
- Payment Management: http://localhost:5000/payments
- Plan Management: http://localhost:5000/plans
- Contact Configuration: http://localhost:5000/contact
- User Management: http://localhost:5000/users
- API - Topup Options: http://localhost:5000/api/topup-options
- API - Payment Methods: http://localhost:5000/api/payment-methods

## Usage

### Bot Commands

- `/start` - Start the bot and show main menu
- `/help` - Show help information
- `/admin` - Admin commands (admin only)
- `/keys` - Check key availability status (admin only)
- `/lowkeys` - Check for plans with low key count (admin only)

### Main Menu Features

**Reply Keyboard Menu (Myanmar Language):**
- 💰 ငွေလက်ကျန် - View account balance and transaction history
- 💳 ငွေဖြည့် - Add credits to account with MMK payment
- 🛒 ပက်ကေ့ချ်ဝယ် - Browse and purchase VPN plans
- 📋 ကျွန်ုပ်၏ပက်ကေ့ချ် - View purchased plans and VPN keys
- 📞 ဆက်သွယ်ရန် - Customer support and contact information

**Plan Purchase Workflow:**
1. User selects "🛒 Buy Plans"
2. Bot shows available plans with credit requirements
3. User selects a plan
4. System checks user balance and key availability
5. If sufficient balance and keys available:
   - Deducts credits from user balance
   - Assigns VPN key to user
   - Creates user plan record
   - Notifies user and admin

**Payment Verification Workflow:**
1. User selects "💳 Topup"
2. User chooses topup amount
3. User receives payment instructions
4. User uploads payment proof image
5. Admin receives notification with approve/deny buttons
6. Admin approves or denies payment
7. If approved: credits added to user balance
8. User receives confirmation

## Project Structure

```
qitopybot/
├── bot.py                    # Main bot file
├── database.py               # Database functions
├── web_admin.py              # Flask admin panel
├── start_admin.py            # Admin panel startup script
├── run_both_simple.py        # Run bot and admin together
├── test_plan_system.py       # Test plan and key system
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .env                     # Your environment variables (create this)
├── templates/               # HTML templates for admin panel
│   ├── base.html
│   ├── dashboard.html
│   ├── topup_management.html
│   ├── payment_management.html
│   ├── plan_management.html
│   ├── add_plan.html
│   ├── edit_plan.html
│   ├── plan_keys.html
│   ├── contact_management.html
│   ├── edit_contact.html
│   └── user_management.html
└── README.md                # This file
```

## Development

### Adding New Features

1. Add new command handlers using `@bot.message_handler(commands=['command'])`
2. Add new menu button handlers using `@bot.message_handler(func=lambda message: message.text == "Button Text")`
3. Create reply keyboards using `ReplyKeyboardMarkup()` and `KeyboardButton()`
4. Create inline keyboards using `InlineKeyboardMarkup()` and `InlineKeyboardButton()`
5. Add callback handlers using `@bot.callback_query_handler(func=lambda call: call.data == "callback_data")`

### Example: Adding a New Inline Button

```python
# Add button to create_inline_menu() function
button5 = InlineKeyboardButton("New Feature", callback_data='new_feature')
markup.add(button5)

# Add callback handler
@bot.callback_query_handler(func=lambda call: call.data == "new_feature")
def handle_new_feature_callback(call):
    bot.answer_callback_query(call.id, "New feature activated!")
    bot.send_message(call.message.chat.id, "New feature response!", reply_markup=create_inline_menu())
```

### Example: Adding a URL Button

```python
# Add URL button
url_button = InlineKeyboardButton("Visit Website", url='https://example.com')
markup.add(url_button)
```

## Security Notes

- Never commit your `.env` file to version control
- Keep your bot token secure
- The `.env` file is already included in `.gitignore`

## Troubleshooting

- Make sure your bot token is correct
- Ensure you have internet connection
- Check that all dependencies are installed
- Verify the bot is not already running elsewhere

## License

This project is open source and available under the MIT License.
