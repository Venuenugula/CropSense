from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram import BotCommand
from bot.handlers import (
    start, set_telugu, set_english,
    help_command, photo_handler,
    location_handler, text_handler,
    voice_handler,               # add this
)
from dotenv import load_dotenv
import os, logging

load_dotenv()

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def post_init(app):
    """Set bot command menu shown to users."""
    await app.bot.set_my_commands([
        BotCommand("start",   "మొదలుపెట్టండి / Start"),
        BotCommand("telugu",  "తెలుగులో మాట్లాడండి"),
        BotCommand("english", "Switch to English"),
        BotCommand("help",    "సహాయం / Help"),
    ])
    logger.info("Bot commands set successfully.")

def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file!")

    print("🌱 Starting Rythu Mitra bot...")
    print("   Bot: @rythumitra_bot")
    print("   Press Ctrl+C to stop.\n")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("telugu",  set_telugu))
    app.add_handler(CommandHandler("english", set_english))
    app.add_handler(CommandHandler("help",    help_command))

    # Messages
    app.add_handler(MessageHandler(filters.PHOTO,    photo_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, text_handler
    ))

    print("✅ Rythu Mitra is running! Open Telegram and send /start to @rythumitra_bot\n")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()