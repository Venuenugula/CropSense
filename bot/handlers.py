from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.pipeline import run_pipeline
from utils.voice import transcribe_audio, text_to_speech_async, detect_language_from_audio
import re
import io
from utils.fertilizer_advisor import (
    find_product, generate_fertilizer_response, handle_unknown_product
)
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
# ─── Fertilizer conversation state ───────────────────────────────────────────
fertilizer_state = {}

async def fertilizer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start fertilizer advisor conversation."""
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")

    fertilizer_state[uid] = {"step": "ask_product", "lang": lang}

    if lang == "telugu":
        await update.message.reply_text(
            "💊 *ఎరువు / మందు సలహా కేంద్రం*\n\n"
            "మీరు వాడాలనుకుంటున్న మందు లేదా ఎరువు పేరు చెప్పండి.\n"
            "ఉదాహరణ: Mancozeb, Urea, DAP, Neem Oil, Imidacloprid\n\n"
            "లేదా మీ దగ్గర ఉన్న పాకెట్ పై ఉన్న పేరు టైప్ చేయండి.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "💊 *Fertilizer & Pesticide Advisor*\n\n"
            "Type the name of the fertilizer or pesticide you want to use.\n"
            "Example: Mancozeb, Urea, DAP, Neem Oil, Imidacloprid\n\n"
            "Or type the name shown on your packet.",
            parse_mode="Markdown"
        )

async def fertilizer_conversation(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    """Handle multi-step fertilizer advisor conversation."""
    uid   = update.effective_user.id
    state = fertilizer_state.get(uid, {})
    lang  = state.get("lang", "telugu")
    text  = update.message.text.strip()
    step  = state.get("step")

    if step == "ask_product":
        product_name, product_data = find_product(text)
        fertilizer_state[uid]["product_query"] = text

        if product_data:
            fertilizer_state[uid]["product_name"] = product_name
            fertilizer_state[uid]["product_data"] = product_data
            fertilizer_state[uid]["step"]         = "ask_crop"

            crops = ", ".join(product_data["target_crops"][:5])
            if lang == "telugu":
                await update.message.reply_text(
                    f"✅ *{product_data['telugu_name']} ({product_name})* దొరికింది!\n\n"
                    f"🌿 ఏ పంటకు వాడుతున్నారు?\n"
                    f"ఉదాహరణ: {crops}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"✅ Found *{product_name}*!\n\n"
                    f"🌿 Which crop are you using it for?\n"
                    f"Example: {crops}",
                    parse_mode="Markdown"
                )
        else:
            # Unknown product — use Gemini general knowledge
            fertilizer_state[uid] = {}
            processing = await update.message.reply_text(
                "🔍 వెతుకుతున్నాం... / Searching..."
            )
            response = handle_unknown_product(text, lang)
            await processing.delete()
            await update.message.reply_text(response, parse_mode="HTML")

            # Send audio
            try:
                whisper_lang = "te" if lang == "telugu" else "en"
                from utils.voice import text_to_speech_async
                audio = await text_to_speech_async(response, language=whisper_lang)
                await update.message.reply_voice(
                    voice=io.BytesIO(audio),
                    caption="💊 Rythu Mitra — Fertilizer Advisor"
                )
            except Exception:
                pass

    elif step == "ask_crop":
        fertilizer_state[uid]["crop"] = text
        fertilizer_state[uid]["step"] = "ask_acres"
        if lang == "telugu":
            await update.message.reply_text(
                f"🌾 మీకు ఎన్ని ఎకరాల {text} పంట ఉంది?\n"
                f"సంఖ్య మాత్రమే టైప్ చేయండి (ఉదా: 2, 0.5, 3.5)"
            )
        else:
            await update.message.reply_text(
                f"🌾 How many acres of {text} do you have?\n"
                f"Type only the number (e.g: 2, 0.5, 3.5)"
            )

    elif step == "ask_acres":
        try:
            acres = float(text.replace("ఎకరాలు", "").replace("acres", "").strip())
            fertilizer_state[uid]["acres"] = acres
            fertilizer_state[uid]["step"]  = "ask_severity"

            if lang == "telugu":
                await update.message.reply_text(
                    "📊 వ్యాధి / సమస్య తీవ్రత ఎంత?\n\n"
                    "1️⃣ తక్కువ (Mild) — కొన్ని మొక్కలు మాత్రమే\n"
                    "2️⃣ మధ్యమం (Medium) — సగం పంట\n"
                    "3️⃣ ఎక్కువ (Severe) — చాలా పంట దెబ్బతింది\n\n"
                    "1, 2 లేదా 3 టైప్ చేయండి",
                    reply_markup=ReplyKeyboardMarkup(
                        [["1 — తక్కువ", "2 — మధ్యమం", "3 — ఎక్కువ"]],
                        one_time_keyboard=True,
                        resize_keyboard=True
                    )
                )
            else:
                await update.message.reply_text(
                    "📊 How severe is the problem?\n\n"
                    "1️⃣ Mild — only a few plants\n"
                    "2️⃣ Medium — about half the crop\n"
                    "3️⃣ Severe — most of the crop affected\n\n"
                    "Type 1, 2 or 3",
                    reply_markup=ReplyKeyboardMarkup(
                        [["1 — Mild", "2 — Medium", "3 — Severe"]],
                        one_time_keyboard=True,
                        resize_keyboard=True
                    )
                )
        except ValueError:
            await update.message.reply_text(
                "⚠️ దయచేసి సంఖ్య మాత్రమే టైప్ చేయండి (ఉదా: 2)\n"
                "Please type only a number (e.g: 2)"
            )

    elif step == "ask_severity":
        severity_map = {
            "1": "mild",   "తక్కువ": "mild",   "mild": "mild",
            "2": "medium", "మధ్యమం": "medium", "medium": "medium",
            "3": "severe", "ఎక్కువ": "severe", "severe": "severe",
        }
        severity = None
        for key, val in severity_map.items():
            if key.lower() in text.lower():
                severity = val
                break

        if not severity:
            await update.message.reply_text(
                "⚠️ 1, 2 లేదా 3 టైప్ చేయండి / Type 1, 2 or 3"
            )
            return

        # Generate full advisory
        processing = await update.message.reply_text(
            "⏳ మోతాదు లెక్కిస్తున్నాం... / Calculating dosage...",
            reply_markup=ReplyKeyboardRemove()
        )

        response = generate_fertilizer_response(
            product_name=state["product_name"],
            product_data=state["product_data"],
            crop=state["crop"],
            acres=state["acres"],
            severity=severity,
            lang=lang,
        )

        await processing.delete()

        response_html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', response)
        response_html = re.sub(r'\*([^*\n]+?)\*', r'<b>\1</b>', response_html)
        await update.message.reply_text(response_html, parse_mode="HTML")

        # Audio
        try:
            whisper_lang = "te" if lang == "telugu" else "en"
            from utils.voice import text_to_speech_async
            audio = await text_to_speech_async(response, language=whisper_lang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption="💊 Rythu Mitra — Fertilizer Guide"
            )
        except Exception:
            pass

        # Clear state
        fertilizer_state.pop(uid, None)

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
    """
    Voice input → always respond with BOTH text + audio immediately.
    No extra prompts. No 'Listen 👇' ask.
    """
    uid   = update.effective_user.id
    state = user_state.get(uid, {})
    lang  = state.get("lang", "telugu")

    # Download voice
    file        = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes = bytes(await file.download_as_bytearray())

    processing_msg = await update.message.reply_text(
        "🎤 వింటున్నాం... / Listening...",
    )

    try:
        # Step 1 — Transcribe
        whisper_lang = "te" if lang == "telugu" else "en"
        transcribed  = transcribe_audio(audio_bytes, language=whisper_lang)

        if not transcribed:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ అర్థం కాలేదు. దయచేసి మళ్ళీ మాట్లాడండి.\n"
                "Could not understand. Please try again."
            )
            return

        # Show what was heard
        await processing_msg.edit_text(
            f"🎤 మీరు చెప్పింది: <i>{transcribed}</i>\n"
            f"⏳ సమాధానం తయారవుతోంది...",
            parse_mode="HTML"
        )

        # Step 2 — If photo waiting → treat voice as district name
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

        # Step 3 — General farming question
        from utils.gemini import call_gemini
        from utils.language import get_system_prompt
        import re

        system = get_system_prompt(lang)
        prompt = f"""
{system}

రైతు ప్రశ్న / Farmer's question: "{transcribed}"

వ్యవసాయ నిపుణుడిగా సులభంగా సమాధానం ఇవ్వండి.
Answer as an agricultural expert in simple {lang} language.
Maximum 4-5 sentences. No bullet points. Conversational tone.
"""
        response     = call_gemini(prompt)
        response_html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', response)
        response_html = re.sub(r'\*([^*\n]+?)\*', r'<b>\1</b>', response_html)

        await processing_msg.delete()

        # Step 4 — Send text + audio TOGETHER immediately
        # Text first
        await update.message.reply_text(
            f"🌱 <b>సమాధానం / Answer:</b>\n\n{response_html}",
            parse_mode="HTML"
        )

        # Audio immediately after — no asking
        from utils.voice import text_to_speech_async
        audio_out = await text_to_speech_async(response, language=whisper_lang)
        await update.message.reply_voice(
            voice=io.BytesIO(audio_out),
            caption="🌱 Rythu Mitra"
        )

    except Exception as e:
        try:
            await processing_msg.delete()
        except Exception:
            pass
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
            user_id=uid,
        )
        await processing_msg.delete()

        response      = result["response"]
        top3          = result["top_predictions"]
        risk          = result["weather_risk"]
        loc_name      = result["location_name"]
        whisper_lang  = "te" if lang == "telugu" else "en"

        # ── 1. Send main disease report text ──────────────────────────────
        response_html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', response)
        response_html = re.sub(r'\*([^*\n]+?)\*', r'<b>\1</b>', response_html)
        response_html = response_html.replace('---', '──────────')
        await update.message.reply_text(response_html, parse_mode="HTML")

        # ── 2. Send top predictions + location + risk ─────────────────────
        conf_text = "📊 <b>Top Predictions:</b>\n"
        for i, p in enumerate(top3, 1):
            disease    = p['disease'].replace('___', ' — ').replace('_', ' ')
            conf_text += f"{i}. {disease} — {p['confidence']}%\n"
        conf_text += (
            f"\n📍 <b>Location:</b> {loc_name}\n"
            f"⛅ <b>Spread Risk:</b> {risk['risk_level']} "
            f"(score: {risk['risk_score']})"
        )
        await update.message.reply_text(conf_text, parse_mode="HTML")

        # ── 3. Send audio of disease report ───────────────────────────────
        await update.message.reply_text(
            "🔊 వింటున్నారా? వ్యాధి వివరాలు వింటారా?\n"
            "🔊 Listen to the disease report 👇"
        )
        try:
            from utils.voice import text_to_speech_async
            audio_bytes = await text_to_speech_async(
                result["response"], language=whisper_lang
            )
            await update.message.reply_voice(
                voice=io.BytesIO(audio_bytes),
                caption="🌱 Rythu Mitra — వ్యాధి నివేదిక / Disease Report"
            )
        except Exception as audio_err:
            print(f"Audio generation failed: {audio_err}")

        # ── 4. Send audio of spread risk advice ───────────────────────────
        try:
            spread_text = (
                f"వ్యాధి వ్యాప్తి ప్రమాదం {risk['risk_level']}గా ఉంది. "
                f"{risk.get('advice', '')} "
                f"{risk.get('reason', '')}"
                if lang == "telugu" else
                f"Disease spread risk is {risk['risk_level']}. "
                f"{risk.get('advice', '')} "
                f"{risk.get('reason', '')}"
            )
            from utils.voice import text_to_speech_async
            risk_audio = await text_to_speech_async(
                spread_text, language=whisper_lang
            )
            await update.message.reply_voice(
                voice=io.BytesIO(risk_audio),
                caption=f"⛅ వ్యాప్తి ప్రమాదం / Spread Risk — {risk['risk_level']}"
            )
        except Exception as risk_audio_err:
            print(f"Risk audio failed: {risk_audio_err}")

        # ── 5. Clear image from state ──────────────────────────────────────
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