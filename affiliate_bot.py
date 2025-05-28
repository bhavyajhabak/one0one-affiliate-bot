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

# === HANDLE ALL TEXT ===
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    bot.send_message(message.chat.id, f"You pressed: {text}")  # Placeholder for logic

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
