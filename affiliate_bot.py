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

# === HANDLE MENU COMMANDS ===
@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    is_admin = user_id in ADMINS

    if user_id not in user_states:
        user_states[user_id] = {"step": None}

    if text == "📥 Register":
        existing_ids = sheet.col_values(3)
        if user_id in existing_ids:
            bot.send_message(message.chat.id, "⚠️ You're already registered.", reply_markup=main_menu(is_admin))
        else:
            bot.send_message(message.chat.id, "Enter your full name:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id] = {"step": "name"}

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
                    f"""📊 *Sales Summary*

🔖 Promo Code: `{promo}`
📦 Total Sales: *{sales}*
💸 Total Earnings: ₹{earnings}
💰 Available Balance: ₹{balance}
📤 Withdrawn So Far: ₹{withdrawn}

👉 Use the *💸 Withdraw* button below when you’re ready to cash out!""",
                    parse_mode='Markdown', reply_markup=main_menu(is_admin))
                return
        bot.send_message(message.chat.id, "❌ Not registered. Tap 📥 Register.", reply_markup=main_menu(is_admin))

    elif text == "💸 Withdraw":
        rows = sheet.get_all_values()
        for row in rows[1:]:
            if row[2] == user_id:
                balance = int(row[8]) if row[8].isdigit() else 0
                user_states[user_id] = {"step": "awaiting_withdraw", "balance": balance}
                bot.send_message(message.chat.id, f"💸 Your balance is ₹{balance}.\nHow much would you like to withdraw?", reply_markup=ReplyKeyboardRemove())
                return
        bot.send_message(message.chat.id, "❌ Not registered. Tap 📥 Register.", reply_markup=main_menu(is_admin))

    elif text == "🛠 Change Code":
        user_states[user_id] = {"step": "change_code"}
        bot.send_message(message.chat.id, "🔤 Enter your new promo code base (we'll add 20 automatically):", reply_markup=ReplyKeyboardRemove())

    elif text == "🏦 Change UPI":
        user_states[user_id] = {"step": "change_upi"}
        bot.send_message(message.chat.id, "🏦 Enter your new UPI ID:", reply_markup=ReplyKeyboardRemove())

    elif text == "🗑 Delete Account":
        user_states[user_id] = {"step": "confirm_delete"}
        bot.send_message(message.chat.id, "⚠️ Type DELETE to confirm account deletion:", reply_markup=ReplyKeyboardRemove())

    elif text in ["📈 Daily Rank", "🏆 All-Time Rank"]:
        rows = sheet.get_all_values()[1:]
        if text == "📈 Daily Rank":
            leaderboard = sorted(rows, key=lambda x: int(x[10]) if x[10].isdigit() else 0, reverse=True)[:10]
            title = "📈 *Top 24H Earners:*"
        else:
            leaderboard = sorted(rows, key=lambda x: int(x[6]) if x[6].isdigit() else 0, reverse=True)[:10]
            title = "🏆 *All-Time Champions:*"

        if not leaderboard:
            bot.send_message(message.chat.id, f"{title}\n\nNo data available.", parse_mode='Markdown', reply_markup=main_menu(is_admin))
        else:
            rank_msg = f"{title}\n\n"
            for idx, row in enumerate(leaderboard, 1):
                name = row[0]
                sales = int(row[10]) if text == "📈 Daily Rank" and row[10].isdigit() else (int(row[6]) if row[6].isdigit() else 0)
                earnings = sales * 20
                rank_msg += f"{idx}. {name} — {sales} sales — ₹{earnings}\n"
            bot.send_message(message.chat.id, rank_msg, parse_mode='Markdown', reply_markup=main_menu(is_admin))

    elif text == "❓ Help":
        bot.send_message(message.chat.id,
            "🤖 *Bot Menu:*\n\n📥 Register – Join the affiliate system\n🧾 Sales – View your sales\n💸 Withdraw – Request payout\n🛠 Change Code – Change your promo code\n🏦 Change UPI – Update your UPI ID\n🗑 Delete Account – Remove yourself\n❓ Help – Show this menu",
            parse_mode='Markdown', reply_markup=main_menu(is_admin))

    else:
        bot.send_message(message.chat.id, "❌ Invalid command or action. Please use the menu.", reply_markup=main_menu(is_admin))
