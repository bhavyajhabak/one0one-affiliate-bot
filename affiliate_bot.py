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

bot = telebot.TeleBot(TOKEN)

# === GOOGLE SHEETS SETUP ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_CREDENTIALS, scope)
client = gspread.authorize(credentials)
sheet = client.open(SHEET_NAME).sheet1

# === TEMP USER STATE ===
user_states = {}

# === MAIN MENU ===
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📥 Register"), KeyboardButton("🧾 Sales"),
        KeyboardButton("💸 Withdraw"), KeyboardButton("🛠 Change Code"),
        KeyboardButton("🏦 Change UPI"), KeyboardButton("🗑 Delete Account"),
        KeyboardButton("📈 Daily Rank"), KeyboardButton("🏆 All-Time Rank"),
        KeyboardButton("❓ Help")
    )
    return markup

# === START COMMAND ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    bot.send_message(message.chat.id,
        "👋 Welcome to the One'0'One Affiliate Bot!\nSelect an option below:",
        reply_markup=main_menu()
    )
    user_states[user_id] = {"step": None}

# === TEXT HANDLER ===
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    if user_id not in user_states:
        user_states[user_id] = {"step": None}

    if text == "📥 Register":
        existing_ids = sheet.col_values(3)
        if user_id in existing_ids:
            bot.send_message(message.chat.id, "⚠ You're already registered.", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "Enter your full name:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id] = {"step": "name"}

    elif text == "📈 Daily Rank" or text == "🏆 All-Time Rank":
        rows = sheet.get_all_values()[1:]
        if text == "📈 Daily Rank":
            leaderboard = sorted(rows, key=lambda x: int(x[10]) if x[10].isdigit() else 0, reverse=True)[:10]
            title = "📈 Top 24H Earners:"
        else:
            leaderboard = sorted(rows, key=lambda x: int(x[6]) if x[6].isdigit() else 0, reverse=True)[:10]
            title = "🏆 All-Time Champions:"

        if not leaderboard:
            bot.send_message(message.chat.id, f"""{title}\n\nNo data available.""", parse_mode='Markdown', reply_markup=main_menu())
        else:
            rank_msg = f"""{title}\n\n"""
            for idx, row in enumerate(leaderboard, 1):
                name = row[0]
                sales = int(row[10]) if text == "📈 Daily Rank" and row[10].isdigit() else (int(row[6]) if row[6].isdigit() else 0)
                earnings = sales * 20
                rank_msg += f"{idx}. {name} — {sales} sales — ₹{earnings}\n"
            bot.send_message(message.chat.id, rank_msg, parse_mode='Markdown', reply_markup=main_menu())

    elif text == "🧾 Sales":
        rows = sheet.get_all_values()
        for row in rows[1:]:
            if row[2] == user_id:
                promo = row[3]
                sales = int(row[6]) if row[6].isdigit() else 0
                earnings = sales * 20
                balance = row[8] if row[8].isdigit() else '0'
                withdrawn = row[9] if row[9].isdigit() else '0'
                bot.send_message(message.chat.id,
                    f"""📊 Sales Summary

🔖 Promo Code: {promo}
📦 Total Sales: {sales}
💸 Total Earnings: ₹{earnings}
💰 Available Balance: ₹{balance}
📤 Withdrawn So Far: ₹{withdrawn}""",
                    parse_mode='Markdown', reply_markup=main_menu())
                return
        bot.send_message(message.chat.id, "❌ Not registered. Tap 📥 Register.", reply_markup=main_menu())

    elif text == "💸 Withdraw":
        rows = sheet.get_all_values()
        for row in rows[1:]:
            if row[2] == user_id:
                balance = int(row[8]) if row[8].isdigit() else 0
                user_states[user_id] = {"step": "awaiting_withdraw", "balance": balance}
                bot.send_message(message.chat.id, f"💸 Your balance is ₹{balance}.\nHow much would you like to withdraw?", reply_markup=ReplyKeyboardRemove())
                return
        bot.send_message(message.chat.id, "❌ Not registered. Tap 📥 Register.", reply_markup=main_menu())

    elif text == "🛠 Change Code":
        user_states[user_id] = {"step": "change_code"}
        bot.send_message(message.chat.id, "🔤 Enter your new promo code base:", reply_markup=ReplyKeyboardRemove())

    elif text == "🏦 Change UPI":
        user_states[user_id] = {"step": "change_upi"}
        bot.send_message(message.chat.id, "🏦 Enter your new UPI ID:", reply_markup=ReplyKeyboardRemove())

    elif text == "🗑 Delete Account":
        user_states[user_id] = {"step": "confirm_delete"}
        bot.send_message(message.chat.id, "⚠ Type DELETE to confirm account deletion:", reply_markup=ReplyKeyboardRemove())

    elif text == "❓ Help":
        bot.send_message(message.chat.id,
            "🤖 Bot Menu:\n\n📥 Register – Join the affiliate system\n🧾 Sales – View your sales\n💸 Withdraw – Request payout\n🛠 Change Code – Change your promo code\n🏦 Change UPI – Update your UPI ID\n🗑 Delete Account – Remove yourself\n❓ Help – Show this menu",
            parse_mode='Markdown', reply_markup=main_menu())

    elif user_states[user_id].get("step"):
        step = user_states[user_id]["step"]
        if step == "name":
            user_states[user_id] = {"step": "code", "name": message.text.strip()}
            bot.send_message(message.chat.id, "Enter your custom promo code base (we'll add 20 automatically):")
        elif step == "code":
            base = message.text.strip()
            new_code = base + "20"
            existing = sheet.col_values(4)
            if new_code.lower() in [x.lower() for x in existing]:
                bot.send_message(message.chat.id, "❌ Code already exists. Try another.")
                return
            user_states[user_id]["code"] = new_code
            user_states[user_id]["step"] = "upi"
            bot.send_message(message.chat.id, "Enter your UPI ID:")
        elif step == "upi":
            upi = message.text.strip()
            state = user_states[user_id]
            sheet.append_row([
                state["name"], message.from_user.username or "N/A", user_id,
                state["code"], upi, "Active", "0", "Pending", "0", "0", "0"])
            bot.send_message(message.chat.id,
                f"✅ Registered!\nPromo Code: {state['code']}\nPayouts to: {upi}\n\n🎉 Share code & earn ₹20/sale.",
                parse_mode='Markdown', reply_markup=main_menu())
            user_states[user_id] = {"step": None}
        elif step == "awaiting_withdraw":
            try:
                req = int(message.text.strip())
                bal = user_states[user_id]["balance"]
                if req > bal:
                    bot.send_message(message.chat.id, f"❌ You only have ₹{bal}. Enter a valid amount.")
                elif req <= 0:
                    bot.send_message(message.chat.id, "❌ Amount must be more than ₹0.")
                else:
                    rows = sheet.get_all_values()
                    for idx, row in enumerate(rows[1:], start=2):
                        if row[2] == user_id:
                            updated_bal = bal - req
                            withdrawn = int(row[9]) if row[9].isdigit() else 0
                            sheet.update_cell(idx, 9, str(withdrawn + req))
                            sheet.update_cell(idx, 8, str(updated_bal))
                            bot.send_message(message.chat.id,
                                f"✅ ₹{req} withdrawal requested. Remaining balance: ₹{updated_bal}", reply_markup=main_menu())
                            break
                    user_states[user_id] = {"step": None}
            except ValueError:
                bot.send_message(message.chat.id, "❌ Enter a valid number.")
        elif step == "change_code":
            base = message.text.strip()
            new_code = base + "20"
            existing = sheet.col_values(4)
            if new_code.lower() in [x.lower() for x in existing]:
                bot.send_message(message.chat.id, "❌ Code already exists. Try another.")
                return
            rows = sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                if row[2] == user_id:
                    sheet.update_cell(idx, 4, new_code)
                    bot.send_message(message.chat.id, f"✅ Promo code updated to {new_code}", reply_markup=main_menu())
                    break
            user_states[user_id] = {"step": None}
        elif step == "change_upi":
            new_upi = message.text.strip()
            rows = sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                if row[2] == user_id:
                    sheet.update_cell(idx, 5, new_upi)
                    bot.send_message(message.chat.id, f"✅ UPI updated to {new_upi}", reply_markup=main_menu())
                    break
            user_states[user_id] = {"step": None}
        elif step == "confirm_delete":
            if message.text.strip().upper() == "DELETE":
                rows = sheet.get_all_values()
                for idx, row in enumerate(rows[1:], start=2):
                    if row[2] == user_id:
                        sheet.delete_rows(idx)
                        bot.send_message(message.chat.id, "✅ Account deleted.", reply_markup=main_menu())
                        break
            else:
                bot.send_message(message.chat.id, "❌ Deletion cancelled.", reply_markup=main_menu())
            user_states[user_id] = {"step": None}

# === FLASK SETUP FOR RENDER ===
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