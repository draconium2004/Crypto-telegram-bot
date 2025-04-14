import logging
import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Your bot token should be set as an environment variable
TOKEN = os.getenv("TOKEN")

# Replace with your actual Telegram user ID(s)
SUBSCRIBERS = [6449591792]

# Set to keep track of already alerted coins (by their pairAddress)
alerted_coins = set()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello Merchant! I'm your Crypto Scout .\n"
        "Use /lowcap to get coins under $200k market cap.\n"
        "Use /alerts to subscribe to new coin alerts."
    )

# /help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Welcome message\n"
        "/lowcap - List coins under $200k mcap (from CoinGecko)\n"
        "/alerts - Subscribe/unsubscribe from new coin alerts"
    )

# /lowcap command handler (using CoinGecko for demo purposes)
async def lowcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_asc",
        "per_page": 10,
        "page": 1,
        "price_change_percentage": "24h",
    }
    response = requests.get(url, params=params)
    data = response.json()

    filtered = [
        coin
        for coin in data
        if coin.get("market_cap", 0) and coin["market_cap"] < 200000
    ]

    if not filtered:
        await update.message.reply_text("No coins under $200k mcap found right now.")
        return

    reply = "\n\n".join(
        [
            f"{coin['name']} ({coin['symbol'].upper()})\nPrice: ${coin['current_price']:,}\nMarket Cap: ${coin['market_cap']:,}"
            for coin in filtered
        ]
    )
    await update.message.reply_text(reply)

# /alerts command handler to show inline keyboard for subscribing
async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Subscribe to new coin alerts", callback_data="subscribe_alerts")
        ],
        [
            InlineKeyboardButton("Unsubscribe from alerts", callback_data="unsubscribe_alerts")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

# Function to fetch and send new coin alerts from Dex Screener for Solana, under $200K mcap
async def new_coin_alerts(context: ContextTypes.DEFAULT_TYPE):
    url = "https://api.dexscreener.com/latest/dex/pairs"
    params = {
        "chain": "solana",
        "page": 1,
        "limit": 10,
    }
    response = requests.get(url, params=params)
    data = response.json()

    for coin in data["pairs"]:
        if coin["market_cap"] and coin["market_cap"] < 200000:
            coin_id = coin["pairAddress"]
            if coin_id not in alerted_coins:
                alerted_coins.add(coin_id)
                message = (
                    f"New Coin Alert! 🚨\n"
                    f"{coin['baseToken']['symbol']} / {coin['quoteToken']['symbol']}\n"
                    f"Price: ${coin['priceUsd']:,}\n"
                    f"Market Cap: ${coin['marketCap']:,}\n"
                    f"View on Dex Screener: {coin['pairUrl']}"
                )
                for subscriber in SUBSCRIBERS:
                    await context.bot.send_message(chat_id=subscriber, text=message)

# Updated button callback function with logging and proper response messages
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    user_id = query.from_user.id
    logging.info(f"Button pressed: {query.data} by user: {user_id}")

    if query.data == "subscribe_alerts":
        if user_id not in SUBSCRIBERS:
            SUBSCRIBERS.append(user_id)
            response_text = "You’ve subscribed to new coin alerts!"
        else:
            response_text = "You are already subscribed to new coin alerts!"
    elif query.data == "unsubscribe_alerts":
        if user_id in SUBSCRIBERS:
            SUBSCRIBERS.remove(user_id)
            response_text = "You’ve unsubscribed from new coin alerts!"
        else:
            response_text = "You are not subscribed!"
    else:
        response_text = "Unknown option!"

    await query.edit_message_text(text=response_text)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lowcap", lowcap))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CallbackQueryHandler(button))

    # Schedule Dex Screener alerts every 20 minutes
    app.job_queue.run_repeating(new_coin_alerts, interval=20 * 60, first=0)

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()