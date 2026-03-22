from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.pipeline import run_pipeline
from utils.voice import transcribe_audio, text_to_speech, detect_language_from_audio
import re
import io
# ─── User state store ────────────────────────────────────────────────────────
user_state = {}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def escape_markdown(text: str) -> str:
    """Escape special chars that break Telegram MarkdownV1."""
    # Only escape chars that break rendering in MarkdownV1
    for ch in ["_", "*", "`", "["]:
        text = text.replace(ch, f"\\{ch}")
    return text

def lang_keyboard():
    return ReplyKeyboardMarkup(
        [["🇮🇳 తెలుగు", "🇬🇧 English"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )

# ─── Command handlers ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "రైతు"
    await update.message.reply_text(
        f"🌱 నమస్కారం {name} గారు!\n\n"
        f"*రైతు మిత్ర* కి స్వాగతం!\n"
        f"మీ పంట వ్యాధులను గుర్తించే AI సహాయకుడు.\n\n"
        f"Hello {name}! Welcome to *Rythu Mitra*!\n"
        f"Your AI crop disease detection assistant.\n\n"
        f"భాష ఎంచుకోండి / Choose your language 👇",
        parse_mode="Markdown",
        reply_markup=lang_keyboard()
    )

async def set_telugu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = {"lang": "telugu"}
    await update.message.reply_text(
        "✅ తెలుగు భాష ఎంచుకున్నారు!\n\n"
        "📸 ఇప్పుడు మీ పంట ఆకు ఫోటో పంపండి.\n"
        "స్పష్టమైన ఫోటో పంపితే మంచి ఫలితాలు వస్తాయి.",
        reply_markup=ReplyKeyboardRemove()
    )

async def set_english(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = {"lang": "english"}
    await update.message.reply_text(
        "✅ English selected!\n\n"
        "📸 Now send a clear photo of your crop leaf.\n"
        "Better photo quality = better detection results.",
        reply_markup=ReplyKeyboardRemove()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌱 *రైతు మిత్ర సహాయం / Rythu Mitra Help*\n\n"
        "ఎలా వాడాలి / How to use:\n"
        "1️⃣ భాష ఎంచుకోండి / Choose language\n"
        "2️⃣ పంట ఫోటో పంపండి / Send crop photo\n"
        "3️⃣ స్థానం పంపండి / Share location\n"
        "4️⃣ వ్యాధి నివేదిక పొందండి / Get disease report\n\n"
        "Commands:\n"
        "/start — మొదలుపెట్టండి / Start over\n"
        "/telugu — తెలుగులో మాట్లాడండి\n"
        "/english — Switch to English\n"
        "/help — సహాయం / Help\n\n"
        "📞 సమస్య వస్తే / Issues: @Venuenugula",
        parse_mode="Markdown"
    )

# ─── Photo handler ────────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")

    # If language not set yet, ask first
    if uid not in user_state:
        await update.message.reply_text(
            "🌱 మొదట భాష ఎంచుకోండి / Please choose language first:",
            reply_markup=lang_keyboard()
        )
        return

    # Download photo
    photo     = update.message.photo[-1]
    file      = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    user_state[uid]["img_bytes"] = bytes(img_bytes)

    # Ask for location
    location_btn = KeyboardButton(
        "📍 మీ స్థానం పంపండి / Share My Location",
        request_location=True
    )
    await update.message.reply_text(
        "📸 ఫోటో అందింది! ✅\n\n"
        "ఇప్పుడు మీ స్థానం పంపండి — 7 రోజుల వ్యాధి వ్యాప్తి ప్రమాదం చెప్తాం.\n\n"
        "Photo received! Now share your location for the 7-day spread risk forecast.\n\n"
        "📍 కింద బటన్ నొక్కండి / Tap button below 👇\n\n"
        "లేదా మీ జిల్లా పేరు టైప్ చేయండి (eg: warangal, karimnagar)\n"
        "Or type your district name if you prefer.",
        reply_markup=ReplyKeyboardMarkup(
            [[location_btn]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

# ─── Location handler ─────────────────────────────────────────────────────────
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = user_state.get(uid, {})

    if "img_bytes" not in state:
        await update.message.reply_text(
            "⚠️ మొదట పంట ఫోటో పంపండి.\n"
            "Please send a crop photo first. 📸"
        )
        return

    lat  = update.message.location.latitude
    lon  = update.message.location.longitude
    lang = state.get("lang", "telugu")

    await _run_and_reply(update, context, uid, state, lat, lon, lang)

# ─── Text handler ─────────────────────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from forecast.weather import resolve_location
    uid   = update.effective_user.id
    state = user_state.get(uid, {})
    text  = update.message.text.strip()

    # Handle language selection buttons
    if "తెలుగు" in text:
        user_state[uid] = user_state.get(uid, {})
        user_state[uid]["lang"] = "telugu"
        await update.message.reply_text(
            "✅ తెలుగు ఎంచుకున్నారు!\n📸 పంట ఫోటో పంపండి.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if "English" in text:
        user_state[uid] = user_state.get(uid, {})
        user_state[uid]["lang"] = "english"
        await update.message.reply_text(
            "✅ English selected!\n📸 Send a photo of your crop.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # No photo yet
    if "img_bytes" not in state:
        await update.message.reply_text(
            "🌱 మొదట పంట ఫోటో పంపండి / Send a crop photo first. 📸\n\n"
            "భాష మార్చాలంటే / To change language:",
            reply_markup=lang_keyboard()
        )
        return

    # Treat text as district name
    lang     = state.get("lang", "telugu")
    lat, lon = resolve_location(text)
    await _run_and_reply(update, context, uid, state, lat, lon, lang,
                         location_label=text)
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages from farmers."""
    uid   = update.effective_user.id
    state = user_state.get(uid, {})
    lang  = state.get("lang", "telugu")

    # Download voice message
    voice     = update.message.voice
    file      = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    processing_msg = await update.message.reply_text(
        "🎤 మీ గొంతు వింటున్నాం... / Listening...\n"
        "⏳ కొంచెం వేచి ఉండండి / Please wait..."
    )

    try:
        # Step 1 — Transcribe voice to text
        whisper_lang = "te" if lang == "telugu" else "en"
        transcribed  = transcribe_audio(bytes(audio_bytes), language=whisper_lang)

        if not transcribed:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ గొంతు అర్థం కాలేదు. దయచేసి మళ్ళీ మాట్లాడండి.\n"
                "Could not understand. Please speak again."
            )
            return

        await update.message.reply_text(
            f"📝 మీరు చెప్పింది / You said:\n_{transcribed}_",
            parse_mode="Markdown"
        )

        # Step 2 — Detect language from transcription
        detected_lang = detect_language_from_audio(transcribed)
        if detected_lang != lang:
            user_state[uid]["lang"] = detected_lang
            lang = detected_lang

        # Step 3 — Check if farmer is asking about disease
        # (has photo in state → treat voice as location fallback)
        if "img_bytes" in state:
            from forecast.weather import resolve_location
            lat, lon = resolve_location(transcribed)
            await processing_msg.delete()
            await _run_and_reply(
                update, context, uid, state,
                lat, lon, lang,
                location_label=transcribed
            )
            return

        # Step 4 — General farming question via Gemini
        await processing_msg.delete()
        processing_msg = await update.message.reply_text(
            "🤔 సమాధానం తయారు చేస్తున్నాం... / Preparing answer..."
        )

        from utils.gemini import call_gemini
        from utils.language import get_system_prompt

        system = get_system_prompt(lang)
        prompt = f"""
{system}

ఒక రైతు ఈ ప్రశ్న అడిగాడు / A farmer asked this question:
"{transcribed}"

వ్యవసాయ నిపుణుడిగా సులభంగా సమాధానం ఇవ్వండి.
Answer as an agricultural expert in simple {lang} language.
Keep the answer concise — maximum 5-6 sentences.
"""
        response = call_gemini(prompt)
        await processing_msg.delete()

        # Step 5 — Send text response
        response_clean = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', response)
        response_clean = re.sub(r'\*([^*\n]+?)\*', r'<b>\1</b>', response_clean)
        await update.message.reply_text(response_clean, parse_mode="HTML")

        # Step 6 — Send voice response back
        await update.message.reply_text(
            "🔊 వినండి / Listen 👇"
        )
        audio_response = text_to_speech(response, language=whisper_lang)
        await update.message.reply_voice(
            voice=io.BytesIO(audio_response),
            caption="🌱 Rythu Mitra"
        )

    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(
            f"❌ లోపం వచ్చింది / Error: <code>{str(e)[:100]}</code>",
            parse_mode="HTML"
        )

# ─── Shared pipeline runner ───────────────────────────────────────────────────
async def _run_and_reply(
    update, context, uid, state,
    lat, lon, lang, location_label=None
):
    label = location_label or f"{lat:.4f}°N, {lon:.4f}°E"
    processing_msg = await update.message.reply_text(
        f"🔍 విశ్లేషిస్తున్నాం... ({label})\n"
        f"Analyzing your crop... please wait ⏳",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        result = run_pipeline(
        image_bytes=state["img_bytes"],
        lat=lat,
        lon=lon,
        lang=lang,
        user_id=uid,        # add this line
    )
        await processing_msg.delete()

        # Send main response — use HTML parse mode to avoid Markdown issues
        response = result["response"]
        # Convert Markdown bold to HTML bold for safety
        response = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', response)
        response = re.sub(r'\*([^*\n]+?)\*', r'<b>\1</b>', response)
        response = response.replace('---', '──────────')
        await update.message.reply_text(response, parse_mode="HTML")

        # Send top predictions
        top3      = result["top_predictions"]
        risk      = result["weather_risk"]
        loc_name  = result["location_name"]
        conf_text = (
            f"📊 <b>Top Predictions:</b>\n"
        )
        for i, p in enumerate(top3, 1):
            disease = p['disease'].replace('___', ' — ').replace('_', ' ')
            conf_text += f"{i}. {disease} — {p['confidence']}%\n"

        conf_text += (
            f"\n📍 <b>Location:</b> {loc_name}\n"
            f"⛅ <b>Spread Risk:</b> {risk['risk_level']} "
            f"(score: {risk['risk_score']})"
        )
        await update.message.reply_text(conf_text, parse_mode="HTML")

        # Clear image from state
        user_state[uid].pop("img_bytes", None)

    except Exception as e:
        await processing_msg.delete()
        err = str(e)[:150]
        await update.message.reply_text(
            f"❌ లోపం వచ్చింది / An error occurred.\n"
            f"దయచేసి మళ్ళీ ప్రయత్నించండి / Please try again.\n\n"
            f"<code>{err}</code>",
            parse_mode="HTML"
        )