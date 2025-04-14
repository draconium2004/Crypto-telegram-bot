import logging
import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Define your bot token and list of subscribers
TOKEN = os.getenv("TOKEN")
SUBSCRIBERS = [6449591792]  # Replace with your Telegram user ID(s)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Store previously alerted coins to avoid duplicates
alerted_coins = set()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey! I'm your Crypto Scout bot. Use /lowcap to get under-200k market cap tokens.\nUse /alerts to subscribe to new coin alerts.")

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\n/start - Welcome message\n/lowcap - Crypto under $200k mcap\n/alerts - Subscribe to alerts for new coins")

# Lowcap command handler
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

# Alerts command handler
async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Subscribe to new coin alerts", callback_data='subscribe_alerts')],
        [InlineKeyboardButton("Unsubscribe from alerts", callback_data='unsubscribe_alerts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

# Fetch and alert new coins from Solana on Dex Screener
async def new_coin_alerts(context: ContextTypes.DEFAULT_TYPE):
    # Dex Screener API URL for Solana coins under $200K market cap
    url = "https://api.dexscreener.com/latest/dex/pairs"
    params = {
        "chain": "solana",
        "page": 1,
        "limit": 10,
    }
    
    response = requests.get(url, params=params)
    data = response.json()

    # Filter new coins under $200K market cap
    for coin in data["pairs"]:
        if coin["market_cap"] and coin["market_cap"] < 200000:
            coin_id = coin["pairAddress"]
            if coin_id not in alerted_coins:
                alerted_coins.add(coin_id)  # Mark the coin as alerted
                message = f"New Coin Alert! 🚨\n{coin['baseToken']['symbol']} / {coin['quoteToken']['symbol']}\nPrice: ${coin['priceUsd']:,}\nMarket Cap: ${coin['marketCap']:,}\nView on Dex Screener: {coin['pairUrl']}"
                
                # Send alerts to subscribers
                for subscriber in SUBSCRIBERS:
                    await context.bot.send_message(chat_id=subscriber, text=message)

# Button handler for alerts subscription
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'subscribe_alerts':
        # Add the user's chat_id to a list of subscribers
        SUBSCRIBERS.append(query.from_user.id)
        await query.edit_message_text("You’ve subscribed to new coin alerts!")
    elif query.data == 'unsubscribe_alerts':
        # Remove the user's chat_id from the list of subscribers
        if query.from_user.id in SUBSCRIBERS:
            SUBSCRIBERS.remove(query.from_user.id)
        await query.edit_message_text("You’ve unsubscribed from new coin alerts!")

# Main function to set up the bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lowcap", lowcap))
    app.add_handler(CommandHandler("alerts", alerts))
    app.add_handler(CallbackQueryHandler(button))

    # Schedule the new coin alerts function to run every 20 minutes
    app.job_queue.run_repeating(new_coin_alerts, interval=20*60, first=0)

    app.run_polling()

if __name__ == '__main__':
    main()