from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue,
    Job,
)
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TRACKED_COINS = ["bitcoin", "ethereum", "solana"]  # CoinGecko IDs
subscribed_users = set()
previous_data = {}

def get_tracked_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'ids': ','.join(TRACKED_COINS),
    }
    response = requests.get(url, params=params)
    return response.json()

async def check_for_changes(context: ContextTypes.DEFAULT_TYPE):
    global previous_data
    application = context.application
    data = get_tracked_coins()

    for coin in data:
        symbol = coin['symbol'].upper()
        name = coin['name']
        market_cap = coin['market_cap']
        volume = coin['total_volume']

        if symbol in previous_data:
            old = previous_data[symbol]
            messages = []

            if market_cap != old['market_cap']:
                messages.append(f"Market Cap changed: {old['market_cap']:,} -> {market_cap:,}")
            if volume != old['volume']:
                messages.append(f"Volume changed: {old['volume']:,} -> {volume:,}")

            if messages:
                alert = f"{name} ({symbol}):\n" + "\n".join(messages)
                for user_id in subscribed_users:
                    await application.bot.send_message(chat_id=user_id, text=alert)

        previous_data[symbol] = {
            'market_cap': market_cap,
            'volume': volume
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribed_users.add(user_id)
    await update.message.reply_text("Welcome! You are now subscribed to market cap/volume alerts.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    subscribed_users.add(user_id)
    await update.message.reply_text("You are now subscribed to updates.")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        await update.message.reply_text("You have been unsubscribed.")
    else:
        await update.message.reply_text("You are not subscribed.")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Schedule check_for_changes to run every 5 minutes
    application.job_queue.run_repeating(check_for_changes, interval=300, first=10)

    print("Bot is running...")
    await application.run_polling()

import asyncio

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # Allows nested event loops, which Railway uses

    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise