"""Localized Telegram / menu (BotCommand descriptions) for English vs Telugu."""
from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeChat

logger = logging.getLogger(__name__)


def commands_telugu() -> list[BotCommand]:
    return [
        BotCommand("start", "మొదలుపెట్టండి"),
        BotCommand("telugu", "తెలుగులోకి మారండి"),
        BotCommand("english", "ఆంగ్లంలోకి మారండి"),
        BotCommand("fertilizer", "💊 ఎరువు / మందు సలహా"),
        BotCommand("mandu", "💊 మందు వివరాలు"),
        BotCommand("schemes", "🏛️ ప్రభుత్వ పథకాలు"),
        BotCommand("pathakalu", "🏛️ పథకాల సమాచారం"),
        BotCommand("calendar", "📅 పంట క్యాలెండర్"),
        BotCommand("panchanga", "📅 నెల వారీ షెడ్యూల్"),
        BotCommand("alerts", "🚨 వ్యాధి వ్యాప్తి నివేదిక"),
        BotCommand("price", "💰 మండి ధరలు"),
        BotCommand("dhara", "💰 పంట ధర తెలుసుకోండి"),
        BotCommand("profile", "👨‍🌾 రైతు ప్రొఫైల్"),
        BotCommand("subscribe", "🔔 ప్రాంతీయ హెచ్చరికలు"),
        BotCommand("checklist", "🗓️ వారపు వ్యవసాయ కార్యాచరణ"),
        BotCommand("help", "సహాయం"),
    ]


def commands_english() -> list[BotCommand]:
    return [
        BotCommand("start", "Start"),
        BotCommand("telugu", "Switch to Telugu"),
        BotCommand("english", "Switch to English"),
        BotCommand("fertilizer", "💊 Fertilizer & pesticide advice"),
        BotCommand("mandu", "💊 Pesticide details"),
        BotCommand("schemes", "🏛️ Government schemes"),
        BotCommand("pathakalu", "🏛️ Scheme information (Telugu)"),
        BotCommand("calendar", "📅 Crop calendar"),
        BotCommand("panchanga", "📅 Monthly schedule"),
        BotCommand("alerts", "🚨 Disease spread alerts"),
        BotCommand("price", "💰 Mandi market prices"),
        BotCommand("dhara", "💰 Crop prices"),
        BotCommand("profile", "👨‍🌾 Farmer profile"),
        BotCommand("subscribe", "🔔 District alert subscription"),
        BotCommand("checklist", "🗓️ Weekly farm checklist"),
        BotCommand("help", "Help"),
    ]


def commands_default_mixed() -> list[BotCommand]:
    """Fallback when Telegram client language is not en/te; still readable for both."""
    return [
        BotCommand("start", "మొదలుపెట్టండి / Start"),
        BotCommand("telugu", "తెలుగులో మాట్లాడండి"),
        BotCommand("english", "Switch to English"),
        BotCommand("fertilizer", "💊 ఎరువు / Fertilizer advice"),
        BotCommand("mandu", "💊 మందు / Pesticide"),
        BotCommand("schemes", "🏛️ పథకాలు / Schemes"),
        BotCommand("pathakalu", "🏛️ పథకాలు / Schemes"),
        BotCommand("calendar", "📅 క్యాలెండర్ / Calendar"),
        BotCommand("panchanga", "📅 షెడ్యూల్ / Schedule"),
        BotCommand("alerts", "🚨 అలర్ట్‌లు / Alerts"),
        BotCommand("price", "💰 ధరలు / Mandi prices"),
        BotCommand("dhara", "💰 ధర / Prices"),
        BotCommand("profile", "👨‍🌾 ప్రొఫైల్ / Profile"),
        BotCommand("subscribe", "🔔 సబ్‌స్క్రిప్షన్ / Subscribe"),
        BotCommand("checklist", "🗓️ చెక్‌లిస్ట్ / Checklist"),
        BotCommand("help", "సహాయం / Help"),
    ]


async def apply_menu_for_language(bot, chat_id: int, lang: str) -> None:
    """Set the / command menu for this private chat to match in-bot language."""
    norm = (lang or "telugu").strip().lower()
    cmds = commands_english() if norm == "english" else commands_telugu()
    try:
        await bot.set_my_commands(cmds, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e:
        logger.warning("set_my_commands (chat scope) failed: %s", e)
