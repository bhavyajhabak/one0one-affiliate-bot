import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
import os
import threading
import time

# === CONFIGURATION ===
TOKEN = '8125239683:AAGOxaitwYGBqM1xK_T2VbCBi6UKigUZd1Y'
SHEET_NAME = 'one0one_affiliates'
JSON_CREDENTIALS = 'one0one-affiliate-bot-b7bf5cb50744.json'
WEBHOOK_URL = f"https://one0one-affiliate-bot.onrender.com/{TOKEN}"
ADMINS = ['7028343866']

bot = telebot.TeleBot(TOKEN)

# === GOOGLE SHEETS SETUP ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_CREDENTIALS, scope)
client = gspread.authorize(credentials)
sheet = client.open(SHEET_NAME).sheet1

# === TEMP USER STATE ===
user_states = {}

# === MAIN MENU ===
def main_menu(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📥 Register"), KeyboardButton("🧾 Sales"),
        KeyboardButton("💸 Withdraw"), KeyboardButton("🛠 Change Code"),
        KeyboardButton("🏦 Change UPI"), KeyboardButton("🗑 Delete Account"),
        KeyboardButton("📈 Daily Rank"), KeyboardButton("🏆 All-Time Rank"),
        KeyboardButton("❓ Help")
    )
    if is_admin:
        markup.add(KeyboardButton("🛠 Admin Panel"))
    return markup

# === START COMMAND ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    is_admin = user_id in ADMINS
    bot.send_message(message.chat.id,
        "👋 Welcome to the One'0'One Affiliate Bot!\nSelect an option below:",
        reply_markup=main_menu(is_admin)
    )
    user_states[user_id] = {"step": None}

# === HANDLE MENU COMMANDS ===
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    is_admin = user_id in ADMINS

    if user_id not in user_states:
        user_states[user_id] = {"step": None}

    if "Register" in text:
        existing_ids = sheet.col_values(3)
        if user_id in existing_ids:
            bot.send_message(message.chat.id, "⚠ You're already registered.", reply_markup=main_menu(is_admin))
        else:
            bot.send_message(message.chat.id, "Enter your full name:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id] = {"step": "name"}

    elif user_states[user_id].get("step") == "name":
        name = text
        user_states[user_id]["name"] = name
        user_states[user_id]["step"] = "code"
        bot.send_message(message.chat.id, "Enter your custom promo code base (we'll add 20 automatically):")

    elif user_states[user_id].get("step") == "code":
        base = text
        new_code = base + "20"
        existing = sheet.col_values(4)
        if new_code.lower() in [x.lower() for x in existing]:
            bot.send_message(message.chat.id, "❌ Code already exists. Try another.")
            return
        user_states[user_id]["code"] = new_code
        user_states[user_id]["step"] = "upi"
        bot.send_message(message.chat.id, "Enter your UPI ID:")

    elif user_states[user_id].get("step") == "upi":
        upi = text
        state = user_states[user_id]
        sheet.append_row([
            state["name"], message.from_user.username or "N/A", user_id,
            state["code"], upi, "Active", "0", "Pending", "0", "0", "0"
        ])
        bot.send_message(message.chat.id,
            f"""✅ Registered!
Promo Code: {state['code']}
Payouts will be sent to: {upi}

🎉 You're now part of the One'0'One Affiliate Army!

🔗 Your job is simple:
1. Share your promo code
2. Earn ₹20 per sale
3. Withdraw anytime using the menu
4. Sell products using our website: [onezeroone.dm2buy.com](https://onezeroone.dm2buy.com)
5. Follow our brand page: [@onezeroone.life](https://instagram.com/onezeroone.life)

💸 You'll be paid within 24 hours after delivery.""",
            parse_mode='Markdown', reply_markup=main_menu(is_admin))
        user_states[user_id] = {"step": None}

    elif "Withdraw" in text:
        bot.send_message(message.chat.id, "Withdraw function goes here.")

    elif "Sales" in text:
        bot.send_message(message.chat.id, "Sales function goes here.")

    elif "Change Code" in text:
        bot.send_message(message.chat.id, "Change code function goes here.")

    elif "Change UPI" in text:
        bot.send_message(message.chat.id, "Change UPI function goes here.")

    elif "Delete Account" in text:
        bot.send_message(message.chat.id, "Delete account function goes here.")

    elif "Daily Rank" in text:
        bot.send_message(message.chat.id, "Daily rank function goes here.")

    elif "All-Time Rank" in text:
        bot.send_message(message.chat.id, "All-time rank function goes here.")

    elif "Help" in text:
        bot.send_message(message.chat.id, "Help menu goes here.")

    elif "Admin Panel" in text and is_admin:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 Pending Withdrawals", "➕ Add Sales", "🔙 Back")
        bot.send_message(message.chat.id, "🛠 Admin Controls:", parse_mode='Markdown', reply_markup=markup)

    else:
        bot.send_message(message.chat.id, "❌ Invalid command or action. Please use the menu.")

# === FLASK SETUP ===
app = Flask(_name_)

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200

@app.route('/')
def home():
    return "✅ Bot is live!", 200

# === DAILY RESET THREAD ===
def reset_daily_sales():
    while True:
        time.sleep(86400)
        try:
            rows = sheet.get_all_values()
            for i in range(2, len(rows)+1):
                sheet.update_cell(i, 11, "0")
            print("✅ Daily sales reset")
        except Exception as e:
            print(f"Error in reset: {e}")

reset_thread = threading.Thread(target=reset_daily_sales)
reset_thread.daemon = True
reset_thread.start()

# === SET WEBHOOK AND RUN ===
if _name_ == "_main_":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)