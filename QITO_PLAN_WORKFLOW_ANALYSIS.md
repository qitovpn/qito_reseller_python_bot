# QITO Plan Workflow Analysis

## 📋 Overview

QITO plans are subscription-based VPN services that are created dynamically via API calls. Unlike regular VPN plans that use pre-generated keys, QITO plans create accounts on-demand through an external API.

---

## 🔄 Complete Workflow Steps

### **Step 1: User Initiates QITO Plan Selection**

**Trigger:** User clicks "🗝 QITO Net" button in Telegram bot

**Handler:** `handle_qito_key()` in `bot.py` (line 698)

**Process:**
1. Ensures user exists in database
2. Queries database for active QITO plans (plans with "QITO" in name)
3. Filters: `WHERE p.name LIKE '%QITO%' AND p.is_active = 1`
4. Displays available QITO plans with inline keyboard buttons
5. Each button has callback: `qito_plan_{plan_id}`

**Output:**
- Message showing all available QITO plans
- Inline keyboard with plan selection buttons

---

### **Step 2: User Selects a QITO Plan**

**Trigger:** User clicks on a QITO plan button

**Handler:** `handle_callback()` - `qito_plan_` callback (line 1395)

**Process:**
1. Extracts plan_id from callback data
2. Retrieves plan details from database using `get_plan(plan_id)`
3. **Balance Check:**
   - Gets user balance: `get_user_balance(user_id)`
   - Converts to credits: `int(balance)` (1:1 conversion)
   - Compares with `credits_required`
4. **If sufficient balance:**
   - Deletes original QITO plans message
   - Shows confirmation dialog with plan details
   - Creates confirmation keyboard with:
     - ✅ Confirm button: `confirm_qito_purchase_{plan_id}`
     - ❌ Cancel button: `cancel_qito_purchase`
5. **If insufficient balance:**
   - Shows error message
   - Prompts user to top up credits

**Confirmation Message Includes:**
- Package ID
- QITO Plan name
- Description
- Duration (days)
- Cost (credits)
- Device limit
- User's current balance

---

### **Step 3: User Confirms Purchase**

**Trigger:** User clicks "✅ QITO ပက်ကေ့ချ် ဝယ်ယူအတည်ပြုပါ"

**Handler:** `handle_callback()` - `confirm_qito_purchase_` callback (line 1480)

**Process:**

#### **3.1 Balance Verification**
- Double-checks user balance
- Ensures sufficient credits before proceeding

#### **3.2 API Call to Create QITO User**
**Function:** `create_qito_user_api(device_limit, duration_days)` (line 74)

**API Details:**
- **URL:** `QITO_API_URL` (from environment: `http://localhost:3000/api/users`)
- **Method:** POST
- **Headers:**
  - Content-Type: application/json
  - User-Agent: Chrome mobile browser
  - Various security headers
- **Request Body:**
  ```json
  {
    "expire_date": "2025-11-25T14:30",  // Calculated: now + duration_days
    "device_limit": 1                    // From plan configuration
  }
  ```
- **Timeout:** 30 seconds

**API Response (Expected):**
```json
{
  "username": "CoolClient168",
  "password": "1hN#3O5Q5Y@V",
  // ... other fields
}
```

#### **3.3 Database Operations**

**If API Call Successful:**

1. **Calculate Dates:**
   - Purchase date: Current datetime
   - Expiry date: Purchase date + duration_days

2. **Insert into `user_plans` table:**
   ```sql
   INSERT INTO user_plans (
     user_id, 
     plan_id, 
     purchase_date, 
     expiry_date, 
     status, 
     vpn_key, 
     api_response
   ) VALUES (?, ?, ?, ?, 'active', ?, ?)
   ```
   - `vpn_key`: Stores `username|password` format
   - `api_response`: Stores full JSON response as text

3. **Deduct Credits:**
   - Calls `add_user_balance(user_id, -credits_required)`
   - Uses ROUND() to prevent decimal precision issues
   - Balance reduced by exact credits required

#### **3.4 User Notification**

**Success Message Includes:**
- ✅ Purchase success confirmation
- Package ID
- QITO Plan name
- Duration
- Cost (credits used)
- Device limit
- Expiry date
- **QITO Account Credentials:**
  - Username (from API response)
  - Password (from API response)
- **QITO Net Account Setup:**
  - Redirect link (from `account_setup_config` table)
  - Configurable via web admin
- Contact information

#### **3.5 Admin Notification**

**If API Call Failed:**
- Shows error message to user
- Does not deduct credits
- Does not create user plan record

**Admin Notification (if successful):**
- Sends message to admin with:
  - User details (name, username, ID)
  - Plan details (ID, name, device limit, duration)
  - Expiry date
  - Credits used
  - QITO credentials (username, password)

---

### **Step 4: User Views Purchased Plans**

**Trigger:** User clicks "📋 ကျွန်ုပ်၏ပက်ကေ့ချ်"

**Handler:** `handle_my_plans()` in `bot.py` (line 646)

**Process:**
1. Retrieves all user plans using `get_user_plans(user_id)`
2. For each plan:
   - Checks if it's a QITO plan (name contains "QITO")
   - If QITO plan:
     - Parses `api_response` JSON
     - Displays QITO username and password
   - If regular VPN plan:
     - Displays VPN key
3. Shows plan details:
   - Plan name
   - Description
   - Purchase date
   - Expiry date
   - Status

---

## 🗄️ Database Structure

### **Plans Table**
```sql
CREATE TABLE plans (
  id INTEGER PRIMARY KEY,
  plan_id_number TEXT UNIQUE,
  name TEXT,                    -- Must contain "QITO" for QITO plans
  description TEXT,
  credits_required INTEGER,
  duration_days INTEGER,
  device_limit INTEGER,
  is_active BOOLEAN
)
```

**QITO Plan Identification:**
- Plans with `name LIKE '%QITO%'` are treated as QITO plans
- No separate table or flag needed

### **User Plans Table**
```sql
CREATE TABLE user_plans (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  plan_id INTEGER,
  purchase_date TIMESTAMP,
  expiry_date TIMESTAMP,
  status TEXT,                  -- 'active', 'expired', etc.
  vpn_key TEXT,                  -- For QITO: "username|password"
  api_response TEXT              -- Full JSON API response
)
```

**QITO Plan Storage:**
- `vpn_key`: Stores credentials as `username|password`
- `api_response`: Stores complete API response JSON
- Both fields used for QITO plan retrieval

---

## 🔧 Key Functions

### **1. `create_qito_user_api(device_limit, duration_days)`**
- **Location:** `bot.py` line 74
- **Purpose:** Creates QITO user account via external API
- **Returns:** API response JSON or None
- **Error Handling:** Catches exceptions, returns None on failure

### **2. `handle_qito_key(message)`**
- **Location:** `bot.py` line 698
- **Purpose:** Displays available QITO plans
- **Process:** Queries database, creates inline keyboard

### **3. `get_user_plans(user_id)`**
- **Location:** `database.py` line 502
- **Purpose:** Retrieves all user's purchased plans
- **Returns:** List of plan tuples including QITO plans

---

## 🌐 Web Admin Management

### **QITO Plan Management Routes**

1. **List QITO Plans:** `/qito`
   - Shows all QITO plans (active and inactive)
   - Displays plan details, credits, duration, device limit

2. **Add QITO Plan:** `/qito/add`
   - Form to create new QITO plan
   - Automatically prefixes name with "QITO"
   - Requires: Plan ID, name, description, credits, duration, device limit

3. **Edit QITO Plan:** `/qito/edit/<plan_id>`
   - Modify existing QITO plan
   - Can activate/deactivate plan
   - Updates all plan fields

4. **Delete QITO Plan:** `/qito/delete/<plan_id>`
   - Removes QITO plan from system
   - Does not affect existing user purchases

5. **QITO Statistics:** `/qito/statistics`
   - Shows QITO plan statistics
   - Purchase analytics
   - Popular plans

---

## 🔐 Security & Error Handling

### **Balance Checks:**
- **Double verification:** Checked before showing confirmation AND before processing
- **Prevents:** Insufficient balance purchases
- **Rounding:** Uses ROUND() to prevent decimal precision issues

### **API Error Handling:**
- **Timeout:** 30 seconds
- **Status codes:** Accepts 200 or 201
- **Failure response:** User notified, no credits deducted
- **Logging:** Errors logged to console

### **Database Transactions:**
- Uses connection retry mechanism
- Proper commit/rollback
- Prevents partial data writes

---

## 📊 Key Differences: QITO vs Regular VPN Plans

| Feature | Regular VPN Plans | QITO Plans |
|---------|------------------|------------|
| **Key Source** | Pre-generated keys in database | Created via API call |
| **Key Storage** | `vpn_keys` table | Not stored (no keys needed) |
| **Account Creation** | Key assignment | API user creation |
| **Credentials** | Single VPN key | Username + Password |
| **Availability Check** | Counts unused keys | No key inventory needed |
| **API Response** | Not used | Stored in `api_response` field |
| **Plan Identification** | No "QITO" in name | Name contains "QITO" |

---

## 🔄 Workflow Diagram

```
User clicks "🗝 QITO Net"
        ↓
Bot displays QITO plans
        ↓
User selects plan
        ↓
Balance check (sufficient?)
        ↓ YES
Show confirmation dialog
        ↓
User confirms purchase
        ↓
Double-check balance
        ↓
Call QITO API
        ↓
API Success?
        ↓ YES
Store in user_plans table
        ↓
Deduct credits from balance
        ↓
Send credentials to user
        ↓
Notify admin
        ↓
Complete ✅
```

---

## 🎯 Configuration

### **Environment Variables:**
- `QITO_API_URL`: QITO API endpoint (default: `http://localhost:3000/api/users`)
- `ADMIN_TELEGRAM_ID`: Admin user ID for notifications

### **Database Configuration:**
- `account_setup_config` table: Stores QITO Net redirect link
- Configurable via web admin: "Account ထည့်နည်း" page

---

## 📝 Notes

1. **No Key Inventory:** QITO plans don't require pre-generated keys
2. **Dynamic Creation:** Accounts created on-demand via API
3. **Subscription-Based:** Different from key-based VPN plans
4. **API Dependency:** System requires QITO API to be available
5. **Error Recovery:** Failed API calls don't affect user balance
6. **Credential Storage:** Username/password stored in `vpn_key` field (pipe-separated)
7. **Full API Response:** Complete API response stored for future reference

---

## ✅ Testing Checklist

- [ ] User can view QITO plans
- [ ] Balance check works correctly
- [ ] Confirmation dialog displays correctly
- [ ] API call succeeds with valid data
- [ ] API call fails gracefully
- [ ] Credits deducted correctly
- [ ] User plan record created
- [ ] Credentials displayed to user
- [ ] Admin notified on purchase
- [ ] Redirect link works
- [ ] User can view purchased QITO plans
- [ ] Decimal precision issues resolved

---

**Last Updated:** Based on current codebase analysis
**Version:** 1.0

