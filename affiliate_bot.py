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
ADMINS = ['7028343866']  # Zemo's Telegram ID

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
        reply_markup=main_menu(is_admin),
        parse_mode=None
    )
    user_states[user_id] = {"step": None}

# === HANDLE ALL MESSAGES ===
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    is_admin = user_id in ADMINS
    if user_id not in user_states:
        user_states[user_id] = {"step": None}

    step = user_states[user_id].get("step")

    if step == "name":
        user_states[user_id]["name"] = text
        user_states[user_id]["step"] = "code"
        bot.send_message(message.chat.id, "Enter your custom promo code base (we'll add 20 automatically):")
        return

    elif step == "code":
        base = text
        new_code = base + "20"
        existing = sheet.col_values(4)
        if new_code.lower() in [x.lower() for x in existing]:
            bot.send_message(message.chat.id, "❌ Code already exists. Try another.")
            return
        user_states[user_id]["code"] = new_code
        user_states[user_id]["step"] = "upi"
        bot.send_message(message.chat.id, "Enter your UPI ID:")
        return

    elif step == "upi":
        upi = text
        state = user_states[user_id]
        sheet.append_row([
            state["name"], message.from_user.username or "N/A", user_id,
            state["code"], upi, "Active", "0", "Pending", "0", "0", "0"
        ])
        bot.send_message(message.chat.id,
            f"""✅ Registered!
Promo Code: `{state['code']}`
Payouts will be sent to: `{upi}`

🎉 You're now part of the One'0'One Affiliate Army!

🔗 Your job is simple:
1. Share your promo code
2. Earn ₹20 per sale
3. Withdraw anytime using the menu
4. Sell products using our website: https://onezeroone.dm2buy.com
5. Follow our brand page: https://instagram.com/onezeroone.life

💸 You'll be paid within 24 hours after delivery.""",
            parse_mode='Markdown', reply_markup=main_menu(is_admin))
        user_states[user_id] = {"step": None}
        return

    # === HANDLE BUTTONS ===
    if text == "📥 Register":
        existing_ids = sheet.col_values(3)
        if user_id in existing_ids:
            bot.send_message(message.chat.id, "⚠️ You're already registered.", reply_markup=main_menu(is_admin))
        else:
            bot.send_message(message.chat.id, "Enter your full name:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id] = {"step": "name"}

    elif text == "❓ Help":
        bot.send_message(message.chat.id,
            "🤖 *Bot Menu:*\n\n📥 Register – Join the affiliate system\n🧾 Sales – View your sales\n💸 Withdraw – Request payout\n🛠 Change Code – Change your promo code\n🏦 Change UPI – Update your UPI ID\n🗑 Delete Account – Remove yourself\n❓ Help – Show this menu",
            parse_mode='Markdown', reply_markup=main_menu(is_admin))

    elif text == "🛠 Admin Panel" and is_admin:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 Pending Withdrawals", "➕ Add Sales", "🔙 Back")
        bot.send_message(message.chat.id, "🛠 *Admin Controls:*", parse_mode='Markdown', reply_markup=markup)

    elif text == "📋 Pending Withdrawals" and is_admin:
        rows = sheet.get_all_values()[1:]
        found = False
        for row in rows:
            if row[7].lower() == "requested":
                found = True
                name = row[0]
                promo = row[3]
                daily_sales = row[10]
                balance = row[8]
                withdraw = row[9]
                bot.send_message(message.chat.id,
                    f"👤 {name}\n🔖 Code: {promo}\n📅 Today: {daily_sales} sales\n💰 Balance: ₹{balance}\n💸 Withdraw: ₹{withdraw}",
                    reply_markup=admin_payment_buttons(row[2]),
                    parse_mode=None)
        if not found:
            bot.send_message(message.chat.id, "✅ No pending withdrawals.")

    elif text == "➕ Add Sales" and is_admin:
        user_states[user_id] = {"step": "add_sales_code"}
        bot.send_message(message.chat.id, "Enter the promo code of the user:")

    elif step == "add_sales_code" and is_admin:
        user_states[user_id]["promo"] = text
        user_states[user_id]["step"] = "add_sales_number"
        bot.send_message(message.chat.id, "How many products were sold?")

    elif step == "add_sales_number" and is_admin:
        try:
            count = int(text)
            promo = user_states[user_id]["promo"]
            rows = sheet.get_all_values()
            for i in range(1, len(rows)):
                if rows[i][3].lower() == promo.lower():
                    total_sales = int(rows[i][6]) + count
                    daily_sales = int(rows[i][10]) + count
                    balance = int(rows[i][8]) + (count * 20)
                    sheet.update_cell(i+1, 6, str(total_sales))
                    sheet.update_cell(i+1, 10, str(daily_sales))
                    sheet.update_cell(i+1, 8, str(balance))
                    bot.send_message(message.chat.id, f"✅ Added {count} sales to {promo}")
                    break
        except:
            bot.send_message(message.chat.id, "❌ Invalid number.")
        user_states[user_id] = {"step": None}

    elif text.startswith("✅ Mark Paid:") and is_admin:
        target_id = text.split(":")[1].strip()
        rows = sheet.get_all_values()
        for i in range(1, len(rows)):
            if rows[i][2] == target_id:
                sheet.update_cell(i+1, 7, "Paid")
                bot.send_message(target_id, "💸 Your withdrawal has been processed and the amount has been credited to your account.")
                bot.send_message(message.chat.id, "✅ User notified.")
                break

    else:
        bot.send_message(message.chat.id, "❌ Invalid command or action. Please use the menu.", reply_markup=main_menu(is_admin))


def admin_payment_buttons(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(f"✅ Mark Paid: {user_id}")
    return markup

# === FLASK SETUP FOR RENDER ===
app = Flask(__name__)

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
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
