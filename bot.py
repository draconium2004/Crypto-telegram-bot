import logging
import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
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

# /start command handler with inline menu buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Low Cap Coins", callback_data="cmd_lowcap")],
        [InlineKeyboardButton("Coin Alerts", callback_data="cmd_alerts")],
        [InlineKeyboardButton("Help", callback_data="cmd_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hello Merchant! I'm your Crypto Scout.\n"
        "Choose an option below to get started:",
        reply_markup=reply_markup,
    )

# /help command handler (also accessible via inline buttons)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Commands:\n"
        "/start - Main menu\n"
        "/lowcap - List coins under $200k mcap (from CoinGecko)\n"
        "/alerts - Subscribe/unsubscribe from new coin alerts"
    )
    # For direct commands you reply as text
    await update.message.reply_text(help_text)

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
    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        logging.error(f"Error fetching CoinGecko data: {e}")
        await update.message.reply_text("Error fetching low cap coins.")
        return

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
            f"{coin['name']} ({coin['symbol'].upper()})\n"
            f"Price: ${coin['current_price']:,}\n"
            f"Market Cap: ${coin['market_cap']:,}"
            for coin in filtered
        ]
    )
    await update.message.reply_text(reply)

# /alerts command handler to show inline keyboard for subscribing/unsubscribing
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

# Function to fetch and send new coin alerts
async def new_coin_alerts(context: ContextTypes.DEFAULT_TYPE):
    url = "https://api.dexscreener.com/latest/dex/pairs"
    params = {
        "chain": "solana",
        "page": 1,
        "limit": 10,
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        logging.error(f"Error fetching Dex Screener data: {e}")
        return

    for coin in data.get("pairs", []):
        # Using the same key names – verify with Dex Screener API docs:
        # Here, if 'market_cap' exists and is lower than 200K, fire an alert.
        if coin.get("market_cap") and coin["market_cap"] < 200000:
            coin_id = coin.get("pairAddress")
            if coin_id and coin_id not in alerted_coins:
                alerted_coins.add(coin_id)
                # Use the correct keys; adjust if necessary (e.g., market_cap vs marketCap)
                message = (
                    f"New Coin Alert! 🚨\n"
                    f"{coin['baseToken']['symbol']} / {coin['quoteToken']['symbol']}\n"
                    f"Price: ${coin['priceUsd']}\n"
                    f"Market Cap: ${coin.get('market_cap', 'N/A')}\n"
                    f"View on Dex Screener: {coin['pairUrl']}"
                )
                for subscriber in SUBSCRIBERS:
                    try:
                        await context.bot.send_message(chat_id=subscriber, text=message)
                    except Exception as send_error:
                        logging.error(f"Error sending message to {subscriber}: {send_error}")

# Button callback handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # acknowledge the button press
    user_id = query.from_user.id
    data = query.data

    logging.info(f"Button pressed: {data} by user: {user_id}")

    if data == "subscribe_alerts":
        if user_id not in SUBSCRIBERS:
            SUBSCRIBERS.append(user_id)
            response_text = "You’ve subscribed to new coin alerts!"
        else:
            response_text = "You are already subscribed to new coin alerts!"
        await query.edit_message_text(text=response_text)

    elif data == "unsubscribe_alerts":
        if user_id in SUBSCRIBERS:
            SUBSCRIBERS.remove(user_id)
            response_text = "You’ve unsubscribed from new coin alerts!"
        else:
            response_text = "You are not subscribed!"
        await query.edit_message_text(text=response_text)

    # Handling inline menu commands from /start
    elif data == "cmd_lowcap":
        # Simulate calling the lowcap function; note that direct function call
        # won't automatically include a message object; instead, we can call the command handler
        # by sending a temporary message.
        try:
            response = await lowcap(update, context)
        except Exception as e:
            logging.error(f"Error handling lowcap command from button: {e}")
            await query.edit_message_text(text="Error fetching low cap coins.")
    elif data == "cmd_alerts":
        # Call alerts command to show subscribe/unsubscribe buttons
        try:
            response = await alerts(update, context)
        except Exception as e:
            logging.error(f"Error handling alerts command from button: {e}")
            await query.edit_message_text(text="Error loading alerts options.")
    elif data == "cmd_help":
        try:
            await help_command(update, context)
            await query.edit_message_text(text="Help info sent to you.")
        except Exception as e:
            logging.error(f"Error handling help command from button: {e}")
            await query.edit_message_text(text="Error loading help info.")
    else:
        await query.edit_message_text(text="Unknown option!")

def main():
    # Build the application using your TOKEN
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lowcap", lowcap))
    app.add_handler(CommandHandler("alerts", alerts))
    
    # Register callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(button))

    # Schedule new coin alerts every 20 minutes
    app.job_queue.run_repeating(new_coin_alerts, interval=20 * 60, first=0)

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()