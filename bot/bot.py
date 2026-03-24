from utils.alert_manager import send_community_alerts

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram import Update
from bot.command_localization import (
    commands_telugu,
    commands_english,
    commands_default_mixed,
)
from bot.handlers import (
    start, set_telugu, set_english, help_command,
    photo_handler, location_handler, voice_handler, text_handler,
    fertilizer_command, fertilizer_conversation, fertilizer_state,
    schemes_command, schemes_conversation, scheme_state,
    route_text, calendar_command, calendar_conversation, calendar_state,
    alerts_command, price_command, price_conversation, price_state,
    profile_command, subscribe_command, checklist_command, feedback_callback,
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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "8000"))


async def error_handler(update, context):
    """Handle errors gracefully — suppress network blips, log real errors."""
    import telegram
    if isinstance(context.error, telegram.error.NetworkError):
        logger.warning(f"Network blip (auto-recovering): {context.error}")
    else:
        logger.error(f"Unhandled error: {context.error}", exc_info=context.error)


async def post_init(application):
    bot = application.bot
    await bot.set_my_commands(commands_telugu(), language_code="te")
    await bot.set_my_commands(commands_english(), language_code="en")
    await bot.set_my_commands(commands_default_mixed())
    logger.info("Bot commands registered (te / en / default). Per-chat menu updates on language choice.")

    async def community_alert_job(context):
        await send_community_alerts(context.bot)

    # Run outbreak alerts every 6 hours using PTB's event-loop-aware job queue.
    application.job_queue.run_repeating(
        community_alert_job,
        interval=6 * 60 * 60,
        first=30,
        name="community_alerts",
    )
    logger.info("Community alert scheduler started (every 6 hours).")


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
    application.add_handler(CommandHandler("calendar",  calendar_command))
    application.add_handler(CommandHandler("panchanga", calendar_command))
    application.add_handler(CommandHandler("alerts",  alerts_command))
    application.add_handler(CommandHandler("price",   price_command))
    application.add_handler(CommandHandler("dhara",   price_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("checklist", checklist_command))

    # Messages
    application.add_handler(MessageHandler(filters.PHOTO,    photo_handler))
    application.add_handler(MessageHandler(filters.VOICE,    voice_handler))
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        route_text
    ))
    application.add_handler(CallbackQueryHandler(feedback_callback, pattern=r"^fb:"))

    # Error handler
    application.add_error_handler(error_handler)

    if WEBHOOK_URL:
        print("✅ Rythu Mitra webhook mode enabled.\n")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        print("✅ Rythu Mitra polling mode enabled.\n")
        application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()