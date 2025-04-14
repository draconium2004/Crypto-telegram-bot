import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")

# For demo: change this to a list or database to store subscribers
SUBSCRIBERS = [@6449591792]  # Replace with your Telegram user ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm your Crypto Scout bot.\n"
        "Use /lowcap to get under-200k market cap tokens.\n"
        "Use /alerts to subscribe to new coin alerts."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Welcome message\n"
        "/lowcap - Crypto under $200k mcap\n"
        "/alerts - Subscribe to alerts for new coins"
    )

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

    filtered = [
        coin for coin in data
        if coin.get("market_cap") and coin["market_cap"] < 200000
    ]

    if not filtered:
        await update.message.reply_text("No coins under $200k mcap found right now.")
        return

    reply = "\n\n".join([
        f"{coin['name']} ({coin['symbol'].upper()})\n"
        f"Price: ${coin['current_price']:,}\n"
        f"Market Cap: ${coin['market_cap']:,}"
        for coin in filtered
    ])
    await update.message.reply_text(reply)

async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Subscribe to new coin alerts", callback_data='subscribe_alerts')],
        [InlineKeyboardButton("Unsubscribe from alerts", callback_data='unsubscribe_alerts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

async def new_coin_alerts(context: ContextTypes.DEFAULT_TYPE):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "gecko_desc",
        "per_page": 5,
        "page": 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    for coin in data:
        message = (
            f"New Coin Alert!\n"
            f"{coin['name']} ({coin['symbol'].upper()})\n"
            f"Price: ${coin['current_price']:,}"
        )

        for chat_id in SUBSCRIBERS:
            await context.bot.send_message(chat_id=chat_id, text=message)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    if query.data == 'subscribe_alerts':
        if chat_id not in SUBSCRIBERS:
            SUBSCRIBERS.append(chat_id)
        await query.edit_message_text("You’ve subscribed to new coin alerts!")

    elif query.data == 'unsubscribe_alerts':
        if chat_id in SUBSCRIBERS:
            SUBSCRIBERS.remove(chat_id)
        await query.edit_message_text("You’ve unsubscribed from alerts!")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lowcap", lowcap))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CallbackQueryHandler(button))

    # Set up JobQueue for periodic new coin alerts
    job_queue = app.job_queue
    job_queue.run_repeating(new_coin_alerts, interval=30 * 60, first=0)

    app.run_polling()

if __name__ == '__main__':
    main()