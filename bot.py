import logging
import os
import requests
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

# Helper function to fetch low-cap coins from CoinGecko
def get_lowcap_text():
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
        return None

    filtered = [
        coin
        for coin in data
        if coin.get("market_cap", 0) and coin["market_cap"] < 200000
    ]
    if not filtered:
        return "No coins under $200k mcap found right now."

    reply = "\n\n".join(
        [
            f"{coin['name']} ({coin['symbol'].upper()})\n"
            f"Price: ${coin['current_price']:,}\n"
            f"Market Cap: ${coin['market_cap']:,}"
            for coin in filtered
        ]
    )
    return reply

# /start command handler with inline menu buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Low Cap Coins", callback_data="cmd_lowcap")],
        [InlineKeyboardButton("Coin Alerts", callback_data="cmd_alerts")],
        [InlineKeyboardButton("Help", callback_data="cmd_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Here update.message exists since it comes from a text command
    await update.message.reply_text(
        "Hello Merchant! I'm your Crypto Scout.\nChoose an option below:",
        reply_markup=reply_markup,
    )

# /help command handler (also accessible via inline button)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Commands:\n"
        "/start - Main menu\n"
        "/lowcap - List coins under $200k mcap (from CoinGecko)\n"
        "/alerts - Subscribe/unsubscribe from new coin alerts"
    )
    if update.message:  # Command context
        await update.message.reply_text(help_text)
    else:
        # For button callbacks, send a new message using chat_id
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=help_text)

# /lowcap command handler
async def lowcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_lowcap_text()
    if not text:
        text = "Error fetching low cap coins."
    if update.message:
        await update.message.reply_text(text)
    else:
        # Use effective_chat id when update.message is not available
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=text)

# /alerts command handler to show subscribe/unsubscribe options
async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Subscribe to new coin alerts", callback_data="subscribe_alerts")],
        [InlineKeyboardButton("Unsubscribe from alerts", callback_data="unsubscribe_alerts")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Choose an option:", reply_markup=reply_markup)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="Choose an option:", reply_markup=reply_markup)

# Function to fetch and send new coin alerts from Dex Screener
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
        if coin.get("market_cap") and coin["market_cap"] < 200000:
            coin_id = coin.get("pairAddress")
            if coin_id and coin_id not in alerted_coins:
                alerted_coins.add(coin_id)
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
    await query.answer()  # Acknowledge the button press
    user_id = query.from_user.id
    data = query.data
    logging.info(f"Button pressed: {data} by user: {user_id}")

    if data == "subscribe_alerts":
        if user_id not in SUBSCRIBERS:
            SUBSCRIBERS.append(user_id)
            response_text = "You've subscribed to new coin alerts!"
        else:
            response_text = "You are already subscribed to new coin alerts!"
        await query.message.reply_text(response_text)

    elif data == "unsubscribe_alerts":
        if user_id in SUBSCRIBERS:
            SUBSCRIBERS.remove(user_id)
            response_text = "You've unsubscribed from new coin alerts!"
        else:
            response_text = "You are not subscribed!"
        await query.message.reply_text(response_text)

    elif data == "cmd_lowcap":
        text = get_lowcap_text()
        if not text:
            text = "Error fetching low cap coins."
        await query.message.reply_text(text)

    elif data == "cmd_alerts":
        keyboard = [
            [InlineKeyboardButton("Subscribe to new coin alerts", callback_data="subscribe_alerts")],
            [InlineKeyboardButton("Unsubscribe from alerts", callback_data="unsubscribe_alerts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Choose an option:", reply_markup=reply_markup)

    elif data == "cmd_help":
        help_text = (
            "Commands:\n"
            "/start - Main menu\n"
            "/lowcap - List coins under $200k mcap (from CoinGecko)\n"
            "/alerts - Subscribe/unsubscribe from new coin alerts"
        )
        await query.message.reply_text(help_text)

    else:
        await query.message.reply_text("Unknown option!")

def main():
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