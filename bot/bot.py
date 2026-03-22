from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram import BotCommand
from bot.handlers import (
    start, set_telugu, set_english, help_command,
    photo_handler, location_handler, voice_handler, text_handler,
    fertilizer_command, fertilizer_conversation, fertilizer_state,
    schemes_command, schemes_conversation, scheme_state,
    route_text,
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


async def error_handler(update, context):
    """Handle errors gracefully — suppress network blips, log real errors."""
    import telegram
    if isinstance(context.error, telegram.error.NetworkError):
        logger.warning(f"Network blip (auto-recovering): {context.error}")
    else:
        logger.error(f"Unhandled error: {context.error}", exc_info=context.error)


async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start",      "మొదలుపెట్టండి / Start"),
        BotCommand("telugu",     "తెలుగులో మాట్లాడండి"),
        BotCommand("english",    "Switch to English"),
        BotCommand("fertilizer", "💊 ఎరువు / మందు సలహా"),
        BotCommand("mandu",      "💊 మందు వివరాలు"),
        BotCommand("schemes",    "🏛️ ప్రభుత్వ పథకాలు"),
        BotCommand("pathakalu",  "🏛️ పథకాల సమాచారం"),
        BotCommand("help",       "సహాయం / Help"),
    ])
    logger.info("Bot commands set successfully.")


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file!")

    print("🌱 Starting Rythu Mitra bot...")
    print("   Bot: @rythumitra_bot")
    print("   Press Ctrl+C to stop.\n")

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    application.add_handler(CommandHandler("start",      start))
    application.add_handler(CommandHandler("telugu",     set_telugu))
    application.add_handler(CommandHandler("english",    set_english))
    application.add_handler(CommandHandler("help",       help_command))
    application.add_handler(CommandHandler("fertilizer", fertilizer_command))
    application.add_handler(CommandHandler("mandu",      fertilizer_command))
    application.add_handler(CommandHandler("schemes",    schemes_command))
    application.add_handler(CommandHandler("pathakalu",  schemes_command))

    # Messages
    application.add_handler(MessageHandler(filters.PHOTO,    photo_handler))
    application.add_handler(MessageHandler(filters.VOICE,    voice_handler))
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        route_text
    ))

    # Error handler
    application.add_error_handler(error_handler)

    print("✅ Rythu Mitra is running! Open Telegram and send /start to @rythumitra_bot\n")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()