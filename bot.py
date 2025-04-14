import logging
import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TOKEN")

# Replace this with your Telegram user ID
SUBSCRIBERS = [6449591792]  # Example: Replace with your actual Telegram user ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey! I'm your Crypto Scout bot. Use /lowcap to get under-200k market cap tokens.\nUse /alerts to subscribe to new coin alerts.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\n/start - Welcome message\n/lowcap - Crypto under $200k mcap\n/alerts - Subscribe to alerts for new coins")

async def lowcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_asc",
        "per_page": 10,
        "page": 1,
        "price_change_percentage": "24h"
    }

    response = requests.get(url, params=params)
    data = response.json()

    filtered = [coin for coin in data if coin.get("market_cap", 0) and coin["market_cap"] < 200000]

    if not filtered:
        await update.message.reply_text("No coins under $200k mcap found right now.")
        return

    reply = "\n\n".join([f"{coin['name']} ({coin['symbol'].upper()})\nPrice: ${coin['current_price']:,}\nMarket Cap: ${coin['market_cap']:,}" for coin in filtered])
    await update.message.reply_text(reply)

async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Subscribe to new coin alerts", callback_data='subscribe_alerts')],
        [InlineKeyboardButton("Unsubscribe from alerts", callback_data='unsubscribe_alerts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

async def new_coin_alerts(context: ContextTypes.DEFAULT_TYPE):
    # Fetch new coins
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "gecko_desc",
        "per_page": 5,
        "page": 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    # Alerting new coins
    for coin in data:
        message = f"New Coin Alert! 🚨\n{coin['name']} ({coin['symbol'].upper()})\nPrice: ${coin['current_price']:,}"
        # Send alerts to users who subscribed
        for subscriber in SUBSCRIBERS:
            await context.bot.send_message(chat_id=subscriber, text=message)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'subscribe_alerts':
        # Here, add the user's chat_id to a list of subscribers
        SUBSCRIBERS.append(update.message.chat_id)  # Example: Add user to subscriber list
        await query.edit_message_text("You’ve subscribed to new coin alerts!")
    elif query.data == 'unsubscribe_alerts':
        # Here, remove the user's chat_id from the list
        SUBSCRIBERS.remove(update.message.chat_id)  # Example: Remove user from subscriber list
        await query.edit_message_text("You’ve unsubscribed from new coin alerts!")

# Manual trigger function
async def manual_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Manually triggering new coin alerts...")
    await new_coin_alerts(context)  # Trigger the alert manually

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Set up handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lowcap", lowcap))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CallbackQueryHandler(button))

    # Add handler for manual trigger
    app.add_handler(CommandHandler("trigger_alerts", manual_alert))  # New command to trigger alerts

    # Schedule new coin alerts every 30 minutes
    app.job_queue.run_repeating(new_coin_alerts, interval=30*60, first=0)  # 30 minutes

    app.run_polling()

if __name__ == '__main__':
    main()