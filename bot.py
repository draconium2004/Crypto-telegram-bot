from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TRACKED_COINS = {"bitcoin": "Bitcoin", "ethereum": "Ethereum", "tether": "USDT"}
subscribed_users = {}  # Now a dictionary with user IDs as keys and selected coins as values
previous_data = {}

def get_tracked_coin_data(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {'localization': 'false'}
    response = requests.get(url, params=params)
    return response.json()

async def check_for_changes(context: ContextTypes.DEFAULT_TYPE):
    global previous_data
    application = context.application

    # Check only for coins subscribed by users
    for user_id, selected_coin in subscribed_users.items():
        coin_data = get_tracked_coin_data(selected_coin)
        symbol = coin_data['symbol'].upper()
        name = coin_data['name']
        market_cap = coin_data['market_data']['market_cap']['usd']
        volume = coin_data['market_data']['total_volume']['usd']

        if symbol in previous_data:
            old = previous_data[symbol]
            messages = []

            if market_cap != old['market_cap']:
                messages.append(f"Market Cap changed: {old['market_cap']:,} -> {market_cap:,}")
            if volume != old['volume']:
                messages.append(f"Volume changed: {old['volume']:,} -> {volume:,}")

            if messages:
                alert = f"{name} ({symbol}):\n" + "\n".join(messages)
                await application.bot.send_message(chat_id=user_id, text=alert)

        previous_data[symbol] = {
            'market_cap': market_cap,
            'volume': volume
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    await update.message.reply_text("Welcome! Type /monitor <coin> to subscribe to a coin (e.g., /monitor bitcoin).")

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Please specify a coin (e.g., /monitor bitcoin).")
        return

    coin = context.args[0].lower()

    if coin in TRACKED_COINS:
        subscribed_users[user_id] = coin
        await update.message.reply_text(f"You have successfully subscribed to {TRACKED_COINS[coin]} updates.")
    else:
        await update.message.reply_text("Invalid coin. Available coins: bitcoin, ethereum, tether.")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id in subscribed_users:
        del subscribed_users[user_id]
        await update.message.reply_text("You have been unsubscribed from all coin updates.")
    else:
        await update.message.reply_text("You are not subscribed to any coin updates.")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Run check every 5 minutes
    app.job_queue.run_repeating(check_for_changes, interval=300, first=10)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()