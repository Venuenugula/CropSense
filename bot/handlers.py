from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.pipeline import run_pipeline
from utils.voice import transcribe_audio, text_to_speech_async, detect_language_from_audio
from utils.crop_calendar import find_crop, generate_calendar_response, get_available_crops
from utils.alert_manager import send_community_alerts, build_alert_message
from db.models import get_outbreak_alerts
from utils.fertilizer_advisor import (
    find_product, generate_fertilizer_response, handle_unknown_product
)
from utils.scheme_advisor import (
    find_relevant_schemes,
    generate_schemes_response,
    search_latest_schemes,
)
from utils.mandi_prices import (
    fetch_mandi_prices, format_price_response, find_crop_name
)
import re
import io

# ─── State stores ─────────────────────────────────────────────────────────────
user_state       = {}
fertilizer_state = {}
scheme_state     = {}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def lang_keyboard():
    return ReplyKeyboardMarkup(
        [["🇮🇳 తెలుగు", "🇬🇧 English"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )

def html(text: str) -> str:
    """Convert markdown bold to HTML bold."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*\n]+?)\*',  r'<b>\1</b>', text)
    text = text.replace('---', '──────────')
    return text

async def send_long_message(message, text: str, parse_mode: str = "HTML"):
    """Split and send messages that exceed Telegram's 4096 char limit."""
    MAX_LEN = 4000
    if len(text) <= MAX_LEN:
        await message.reply_text(text, parse_mode=parse_mode)
        return

    # Split at paragraph boundaries
    parts   = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 <= MAX_LEN:
            current += paragraph + "\n\n"
        else:
            if current:
                parts.append(current.strip())
            current = paragraph + "\n\n"
    if current:
        parts.append(current.strip())

    for part in parts:
        await message.reply_text(part, parse_mode=parse_mode)

# ─── Central text router ──────────────────────────────────────────────────────
async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in fertilizer_state:
        await fertilizer_conversation(update, context)
    elif uid in scheme_state:
        await schemes_conversation(update, context)
    elif uid in calendar_state:
        await calendar_conversation(update, context)
    elif uid in price_state:
        await price_conversation(update, context)
    else:
        await text_handler(update, context)
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
        "📸 ఇప్పుడు మీ పంట ఆకు ఫోటో పంపండి.",
        reply_markup=ReplyKeyboardRemove()
    )

async def set_english(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = {"lang": "english"}
    await update.message.reply_text(
        "✅ English selected!\n\n"
        "📸 Now send a clear photo of your crop leaf.",
        reply_markup=ReplyKeyboardRemove()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌱 *రైతు మిత్ర సహాయం / Help*\n\n"
        "Commands:\n"
        "/start — మొదలుపెట్టండి\n"
        "/telugu — తెలుగులో మాట్లాడండి\n"
        "/english — Switch to English\n"
        "/fertilizer — 💊 ఎరువు / మందు సలహా\n"
        "/schemes — 🏛️ ప్రభుత్వ పథకాలు\n"
        "/help — సహాయం\n\n"
        "📞 సమస్య వస్తే: @Venuenugula",
        parse_mode="Markdown"
    )

# ─── Photo handler ────────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")

    if uid not in user_state:
        await update.message.reply_text(
            "🌱 మొదట భాష ఎంచుకోండి / Please choose language first:",
            reply_markup=lang_keyboard()
        )
        return

    photo     = update.message.photo[-1]
    file      = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()
    user_state[uid]["img_bytes"] = bytes(img_bytes)

    location_btn = KeyboardButton(
        "📍 మీ స్థానం పంపండి / Share My Location",
        request_location=True
    )
    await update.message.reply_text(
        "📸 ఫోటో అందింది! ✅\n\n"
        "ఇప్పుడు మీ స్థానం పంపండి — 7 రోజుల వ్యాధి వ్యాప్తి ప్రమాదం చెప్తాం.\n\n"
        "📍 కింద బటన్ నొక్కండి / Tap button below 👇\n\n"
        "లేదా మీ జిల్లా పేరు టైప్ చేయండి (eg: warangal, karimnagar)",
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
            "⚠️ మొదట పంట ఫోటో పంపండి.\nPlease send a crop photo first. 📸"
        )
        return

    lat  = update.message.location.latitude
    lon  = update.message.location.longitude
    lang = state.get("lang", "telugu")
    await _run_and_reply(update, context, uid, state, lat, lon, lang)

# ─── Voice handler ────────────────────────────────────────────────────────────
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles voice in ALL contexts:
    - During fertilizer/scheme conversation → transcribe + route correctly
    - After photo → treat as district name
    - Otherwise → answer farming question with text + audio
    """
    uid   = update.effective_user.id
    state = user_state.get(uid, {})
    lang  = state.get("lang", "telugu")

    file        = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes = bytes(await file.download_as_bytearray())

    processing_msg = await update.message.reply_text("🎤 వింటున్నాం... / Listening...")

    try:
        whisper_lang = "te" if lang == "telugu" else "en"
        transcribed  = transcribe_audio(audio_bytes, language=whisper_lang)

        if not transcribed:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ అర్థం కాలేదు. దయచేసి మళ్ళీ మాట్లాడండి.\n"
                "Could not understand. Please try again."
            )
            return

        await processing_msg.edit_text(
            f"🎤 మీరు చెప్పింది: <i>{transcribed}</i>\n⏳ సమాధానం తయారవుతోంది...",
            parse_mode="HTML"
        )

        # Route to active conversation
        if uid in fertilizer_state or uid in scheme_state or uid in calendar_state or uid in price_state:
            update.message.text = transcribed
            await processing_msg.delete()
            if uid in fertilizer_state:
                await fertilizer_conversation(update, context)
            elif uid in scheme_state:
                await schemes_conversation(update, context)
            elif uid in calendar_state:
                await calendar_conversation(update, context)
            elif uid in price_state:
                await price_conversation(update, context)
            return

        # If photo is waiting → treat voice as location
        if "img_bytes" in state:
            from forecast.weather import resolve_location
            lat, lon = resolve_location(transcribed)
            await processing_msg.delete()
            await _run_and_reply(
                update, context, uid, state,
                lat, lon, lang, location_label=transcribed
            )
            return

        # General farming Q&A
        from utils.gemini import call_gemini
        from utils.language import get_system_prompt

        system = get_system_prompt(lang)
        prompt = f"""
{system}

రైతు ప్రశ్న / Farmer's question: "{transcribed}"

వ్యవసాయ నిపుణుడిగా సులభంగా సమాధానం ఇవ్వండి.
Answer in simple {lang} language. Max 4-5 sentences. Conversational tone.
"""
        response = call_gemini(prompt)
        await processing_msg.delete()

        await send_long_message(
            update.message,
            f"🌱 <b>సమాధానం / Answer:</b>\n\n{html(response)}"
        )
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
# ─── Calendar handlers ────────────────────────────────────────────────────────
calendar_state = {}

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")
    calendar_state[uid] = {"step": "ask_crop", "lang": lang}

    available = get_available_crops()
    if lang == "telugu":
        await update.message.reply_text(
            "📅 *పంట క్యాలెండర్*\n\n"
            "మీ పంట పేరు చెప్పండి:\n\n"
            f"అందుబాటులో ఉన్న పంటలు:\n{available}\n\n"
            "ఉదాహరణ: వరి, టమాటో, పత్తి, వేరుశెనగ",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["వరి", "టమాటో"], ["పత్తి", "వేరుశెనగ"], ["మొక్కజొన్న"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            "📅 *Crop Calendar*\n\n"
            "Which crop do you want the calendar for?\n\n"
            f"Available crops: {available}",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["Rice", "Tomato"], ["Cotton", "Groundnut"], ["Maize"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current disease outbreaks in Telangana."""
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")

    alerts = get_outbreak_alerts()

    if not alerts:
        msg = (
            "✅ ప్రస్తుతం మీ ప్రాంతంలో వ్యాధి వ్యాప్తి నివేదికలు లేవు.\n"
            "Your area is clear — no disease outbreaks reported."
            if lang == "telugu" else
            "✅ No disease outbreaks reported in your area currently.\n"
            "Keep monitoring your crops weekly."
        )
        await update.message.reply_text(msg)
        return

    if lang == "telugu":
        response = "🚨 <b>ప్రస్తుత వ్యాధి వ్యాప్తి నివేదిక</b>\n\n"
    else:
        response = "🚨 <b>Current Disease Outbreak Report</b>\n\n"

    for alert in alerts[:5]:
        response += build_alert_message(alert, lang) + "\n\n"

    await send_long_message(update.message, response)
async def calendar_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = calendar_state.get(uid, {})
    lang  = state.get("lang", "telugu")
    text  = (update.message.text or "").strip()

    if state.get("step") == "ask_crop":
        crop_name, crop_data = find_crop(text)

        if not crop_data:
            available = get_available_crops()
            await update.message.reply_text(
                f"⚠️ '{text}' పంట దొరకలేదు.\n\n"
                f"అందుబాటులో ఉన్న పంటలు: {available}",
                reply_markup=ReplyKeyboardMarkup(
                    [["వరి", "టమాటో"], ["పత్తి", "వేరుశెనగ"], ["మొక్కజొన్న"]],
                    one_time_keyboard=True, resize_keyboard=True
                )
            )
            return

        calendar_state.pop(uid, None)
        processing = await update.message.reply_text(
            f"📅 {crop_data['telugu_name']} పంట క్యాలెండర్ తయారు చేస్తున్నాం...\n"
            f"Preparing {crop_name} crop calendar... ⏳",
            reply_markup=ReplyKeyboardRemove()
        )

        response = generate_calendar_response(crop_name, crop_data, lang)
        await processing.delete()
        await send_long_message(update.message, html(response))

        # Audio
        try:
            wlang = "te" if lang == "telugu" else "en"
            audio = await text_to_speech_async(response, language=wlang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption=f"📅 Rythu Mitra — {crop_data['telugu_name']} పంట క్యాలెండర్"
            )
        except Exception as e:
            print(f"Calendar audio failed: {e}")
# ─── Mandi price state ────────────────────────────────────────────────────────
price_state = {}

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")
    price_state[uid] = {"step": "ask_crop", "lang": lang}

    if lang == "telugu":
        await update.message.reply_text(
            "💰 *మండి ధరల కేంద్రం*\n\n"
            "ఏ పంట ధర కావాలి?\n\n"
            "ఉదాహరణ: వరి, టమాటో, పత్తి, వేరుశెనగ, ఉల్లి",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["వరి", "టమాటో", "పత్తి"],
                 ["వేరుశెనగ", "మొక్కజొన్న", "ఉల్లి"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            "💰 *Mandi Price Checker*\n\n"
            "Which crop price do you want?\n\n"
            "Example: Rice, Tomato, Cotton, Groundnut, Onion",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["Rice", "Tomato", "Cotton"],
                 ["Groundnut", "Maize", "Onion"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )

async def price_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = price_state.get(uid, {})
    lang  = state.get("lang", "telugu")
    text  = (update.message.text or "").strip()

    if state.get("step") == "ask_crop":
        price_state.pop(uid, None)

        processing = await update.message.reply_text(
            f"🔍 {text} ధరలు తీసుకుంటున్నాం...\nFetching live prices... ⏳",
            reply_markup=ReplyKeyboardRemove()
        )

        records, date, crop_name = fetch_mandi_prices(text)
        response = format_price_response(records, text, crop_name, date, lang)

        await processing.delete()
        await send_long_message(update.message, response)

        # Audio
        try:
            wlang = "te" if lang == "telugu" else "en"
            audio = await text_to_speech_async(response, language=wlang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption=f"💰 Rythu Mitra — {text} మండి ధరలు"
            )
        except Exception as e:
            print(f"Price audio failed: {e}")

# ─── Text handler ─────────────────────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from forecast.weather import resolve_location
    uid   = update.effective_user.id
    state = user_state.get(uid, {})
    text  = update.message.text.strip()

    # Language selection buttons
    if "తెలుగు" in text:
        user_state.setdefault(uid, {})["lang"] = "telugu"
        await update.message.reply_text(
            "✅ తెలుగు ఎంచుకున్నారు!\n📸 పంట ఫోటో పంపండి.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if "English" in text:
        user_state.setdefault(uid, {})["lang"] = "english"
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

    # Treat text as district name for location
    lang     = state.get("lang", "telugu")
    lat, lon = resolve_location(text)
    await _run_and_reply(update, context, uid, state, lat, lon, lang,
                         location_label=text)

# ─── Fertilizer handlers ──────────────────────────────────────────────────────
async def fertilizer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")
    fertilizer_state[uid] = {"step": "ask_product", "lang": lang}

    if lang == "telugu":
        await update.message.reply_text(
            "💊 *ఎరువు / మందు సలహా కేంద్రం*\n\n"
            "మీరు వాడాలనుకుంటున్న మందు లేదా ఎరువు పేరు చెప్పండి.\n"
            "ఉదాహరణ: Mancozeb, Urea, DAP, Neem Oil, Imidacloprid\n\n"
            "లేదా మీ పాకెట్ పై ఉన్న పేరు టైప్ చేయండి.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "💊 *Fertilizer & Pesticide Advisor*\n\n"
            "Type the name of the fertilizer or pesticide.\n"
            "Example: Mancozeb, Urea, DAP, Neem Oil, Imidacloprid",
            parse_mode="Markdown"
        )

async def fertilizer_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = fertilizer_state.get(uid, {})
    lang  = state.get("lang", "telugu")
    text  = (update.message.text or "").strip()
    step  = state.get("step")

    if step == "ask_product":
        product_name, product_data = find_product(text)
        fertilizer_state[uid]["product_query"] = text

        if product_data:
            fertilizer_state[uid].update({
                "product_name": product_name,
                "product_data": product_data,
                "step":         "ask_crop",
            })
            crops = ", ".join(product_data["target_crops"][:5])
            msg = (
                f"✅ *{product_data['telugu_name']} ({product_name})* దొరికింది!\n\n"
                f"🌿 ఏ పంటకు వాడుతున్నారు?\nఉదాహరణ: {crops}"
                if lang == "telugu" else
                f"✅ Found *{product_name}*!\n\n"
                f"🌿 Which crop are you using it for?\nExample: {crops}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            fertilizer_state.pop(uid, None)
            processing = await update.message.reply_text("🔍 వెతుకుతున్నాం... / Searching...")
            response   = handle_unknown_product(text, lang)
            await processing.delete()
            await send_long_message(update.message, html(response))
            try:
                wlang = "te" if lang == "telugu" else "en"
                audio = await text_to_speech_async(response, language=wlang)
                await update.message.reply_voice(voice=io.BytesIO(audio), caption="💊 Rythu Mitra")
            except Exception:
                pass

    elif step == "ask_crop":
        fertilizer_state[uid]["crop"] = text
        fertilizer_state[uid]["step"] = "ask_acres"
        msg = (
            f"🌾 మీకు ఎన్ని ఎకరాల {text} పంట ఉంది?\nసంఖ్య మాత్రమే టైప్ చేయండి (ఉదా: 2, 0.5, 3.5)"
            if lang == "telugu" else
            f"🌾 How many acres of {text} do you have?\nType only the number (e.g: 2, 0.5, 3.5)"
        )
        await update.message.reply_text(msg)

    elif step == "ask_acres":
        try:
            acres = float(text.replace("ఎకరాలు", "").replace("acres", "").strip())
            fertilizer_state[uid]["acres"] = acres
            fertilizer_state[uid]["step"]  = "ask_severity"
            if lang == "telugu":
                await update.message.reply_text(
                    "📊 వ్యాధి తీవ్రత ఎంత?\n\n"
                    "1️⃣ తక్కువ — కొన్ని మొక్కలు మాత్రమే\n"
                    "2️⃣ మధ్యమం — సగం పంట\n"
                    "3️⃣ ఎక్కువ — చాలా పంట దెబ్బతింది\n\n"
                    "1, 2 లేదా 3 టైప్ చేయండి",
                    reply_markup=ReplyKeyboardMarkup(
                        [["1 — తక్కువ", "2 — మధ్యమం", "3 — ఎక్కువ"]],
                        one_time_keyboard=True, resize_keyboard=True
                    )
                )
            else:
                await update.message.reply_text(
                    "📊 How severe is the problem?\n\n"
                    "1️⃣ Mild — only a few plants\n"
                    "2️⃣ Medium — about half the crop\n"
                    "3️⃣ Severe — most of the crop affected\n\nType 1, 2 or 3",
                    reply_markup=ReplyKeyboardMarkup(
                        [["1 — Mild", "2 — Medium", "3 — Severe"]],
                        one_time_keyboard=True, resize_keyboard=True
                    )
                )
        except ValueError:
            await update.message.reply_text(
                "⚠️ దయచేసి సంఖ్య మాత్రమే టైప్ చేయండి (ఉదా: 2)\nPlease type only a number (e.g: 2)"
            )

    elif step == "ask_severity":
        severity_map = {
            "1": "mild",   "తక్కువ": "mild",   "mild": "mild",
            "2": "medium", "మధ్యమం": "medium", "medium": "medium",
            "3": "severe", "ఎక్కువ": "severe", "severe": "severe",
        }
        severity = next(
            (v for k, v in severity_map.items() if k.lower() in text.lower()),
            None
        )
        if not severity:
            await update.message.reply_text("⚠️ 1, 2 లేదా 3 టైప్ చేయండి / Type 1, 2 or 3")
            return

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
        await send_long_message(update.message, html(response))
        try:
            wlang = "te" if lang == "telugu" else "en"
            audio = await text_to_speech_async(response, language=wlang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption="💊 Rythu Mitra — Fertilizer Guide"
            )
        except Exception:
            pass
        fertilizer_state.pop(uid, None)

# ─── Scheme handlers ──────────────────────────────────────────────────────────
async def schemes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_state.get(uid, {}).get("lang", "telugu")
    scheme_state[uid] = {"step": "ask_district", "lang": lang}

    if lang == "telugu":
        await update.message.reply_text(
            "🏛️ *ప్రభుత్వ పథకాల కేంద్రం*\n\n"
            "మీ జిల్లా పేరు చెప్పండి:\n"
            "ఉదాహరణ: వరంగల్, కరీంనగర్, నిజామాబాద్, బాసర",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🏛️ *Government Scheme Finder*\n\n"
            "Tell me your district name:\n"
            "Example: Warangal, Karimnagar, Nizamabad, Basar",
            parse_mode="Markdown"
        )

async def schemes_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = scheme_state.get(uid, {})
    lang  = state.get("lang", "telugu")
    text  = (update.message.text or "").strip()
    step  = state.get("step")

    if step == "ask_district":
        scheme_state[uid]["district"] = text
        scheme_state[uid]["step"]     = "ask_crop"
        msg = (
            f"✅ {text} జిల్లా!\n\n"
            f"🌾 మీరు ఏ పంట పండిస్తున్నారు?\n"
            f"ఉదాహరణ: వరి, టమాటో, మొక్కజొన్న, వేరుశెనగ, పత్తి"
            if lang == "telugu" else
            f"✅ {text} district!\n\n"
            f"🌾 Which crop do you grow?\n"
            f"Example: Rice, Tomato, Maize, Groundnut, Cotton"
        )
        await update.message.reply_text(msg)

    elif step == "ask_crop":
        district = state["district"]
        crop     = text
        scheme_state[uid]["crop"] = crop

        processing = await update.message.reply_text(
            "🔍 పథకాలు వెతుకుతున్నాం + తాజా సమాచారం తీసుకుంటున్నాం...\n"
            "Searching schemes + fetching latest updates... ⏳"
        )

        schemes     = find_relevant_schemes(crop=crop, district=district)
        latest_info = search_latest_schemes()
        response    = generate_schemes_response(
            schemes=schemes, crop=crop, district=district,
            lang=lang, latest_info=latest_info,
        )

        await processing.delete()
        await send_long_message(update.message, html(response))

        try:
            wlang = "te" if lang == "telugu" else "en"
            audio = await text_to_speech_async(response, language=wlang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption="🏛️ Rythu Mitra — Government Schemes"
            )
        except Exception as e:
            print(f"Schemes audio failed: {e}")

        scheme_state.pop(uid, None)

# ─── Pipeline runner ──────────────────────────────────────────────────────────
async def _run_and_reply(
    update, context, uid, state,
    lat, lon, lang, location_label=None
):
    label          = location_label or f"{lat:.4f}°N, {lon:.4f}°E"
    processing_msg = await update.message.reply_text(
        f"🔍 విశ్లేషిస్తున్నాం... ({label})\nAnalyzing your crop... please wait ⏳",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        result = run_pipeline(
            image_bytes=state["img_bytes"],
            lat=lat, lon=lon, lang=lang, user_id=uid,
        )
        await processing_msg.delete()

        response     = result["response"]
        top3         = result["top_predictions"]
        risk         = result["weather_risk"]
        loc_name     = result["location_name"]
        whisper_lang = "te" if lang == "telugu" else "en"

        # Disease report text
        await send_long_message(update.message, html(response))

        # Predictions + risk summary
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

        # Disease report audio
        try:
            audio = await text_to_speech_async(response, language=whisper_lang)
            await update.message.reply_voice(
                voice=io.BytesIO(audio),
                caption="🌱 Rythu Mitra — వ్యాధి నివేదిక / Disease Report"
            )
        except Exception as e:
            print(f"Disease audio failed: {e}")

        # Spread risk audio
        try:
            spread_text = (
                f"వ్యాధి వ్యాప్తి ప్రమాదం {risk['risk_level']}గా ఉంది. "
                f"{risk.get('advice', '')} {risk.get('reason', '')}"
                if lang == "telugu" else
                f"Disease spread risk is {risk['risk_level']}. "
                f"{risk.get('advice', '')} {risk.get('reason', '')}"
            )
            risk_audio = await text_to_speech_async(spread_text, language=whisper_lang)
            await update.message.reply_voice(
                voice=io.BytesIO(risk_audio),
                caption=f"⛅ వ్యాప్తి ప్రమాదం / Spread Risk — {risk['risk_level']}"
            )
        except Exception as e:
            print(f"Risk audio failed: {e}")

        user_state[uid].pop("img_bytes", None)

    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(
            f"❌ లోపం వచ్చింది / An error occurred.\n"
            f"దయచేసి మళ్ళీ ప్రయత్నించండి / Please try again.\n\n"
            f"<code>{str(e)[:150]}</code>",
            parse_mode="HTML"
        )