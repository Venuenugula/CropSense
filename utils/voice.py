import os
import io
import tempfile
import base64
import re
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

# ─── Clients ─────────────────────────────────────────────────────────────────
def _groq_client():
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def _gemini_client():
    from google import genai
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ─── Transcription ───────────────────────────────────────────────────────────
def transcribe_audio(audio_bytes: bytes, language: str = "te") -> str:
    """
    Telugu → use Gemini (far more accurate for Telugu).
    English → use Groq Whisper.
    """
    if language == "te":
        return _transcribe_gemini_telugu(audio_bytes)
    else:
        return _transcribe_groq(audio_bytes, language)


def _transcribe_gemini_telugu(audio_bytes: bytes) -> str:
    """Use Gemini 2.5 Flash to transcribe Telugu audio — best accuracy."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            audio_file = genai.upload_file(tmp_path, mime_type="audio/ogg")
            model      = genai.GenerativeModel("gemini-2.0-flash")
            result     = model.generate_content([
                audio_file,
                """This is a Telugu farmer speaking about crops, farming, diseases, or fertilizers.
Please transcribe exactly what was said in Telugu script (తెలుగు లిపిలో రాయండి).
If some words are in English (like fertilizer names), keep them in English.
Return ONLY the transcription, nothing else."""
            ])
            return result.text.strip()
        finally:
            os.unlink(tmp_path)
            try:
                genai.delete_file(audio_file.name)
            except Exception:
                pass

    except Exception as e:
        print(f"Gemini transcription failed: {e} — falling back to Groq")
        return _transcribe_groq(audio_bytes, "te")


def _transcribe_groq(audio_bytes: bytes, language: str = "en") -> str:
    """Groq Whisper — used for English and as Telugu fallback."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        client = _groq_client()
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language=language,
                response_format="text",
                prompt=(
                    "Telugu farmer asking about crops, diseases, fertilizers."
                    if language == "te" else
                    "Farmer asking about crops, diseases or farming."
                ),
            )
        return result.strip()
    finally:
        os.unlink(tmp_path)


# ─── Text to Speech ───────────────────────────────────────────────────────────
def text_to_speech(text: str, language: str = "te") -> bytes:
    """Sync fallback TTS using gTTS."""
    clean = re.sub(r'<[^>]+>', '', text)
    for ch in ["*", "_", "`", "#", "•", "---"]:
        clean = clean.replace(ch, "")
    clean = clean.strip()
    gtts_lang = "te" if language == "te" else "en"
    tts = gTTS(text=clean, lang=gtts_lang, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
async def text_to_speech_async(text: str, language: str = "te") -> bytes:
    """Better quality TTS using Microsoft Edge TTS (free)."""
    import edge_tts
    import asyncio

    clean = re.sub(r'<[^>]+>', '', text)
    for ch in ["*", "_", "`", "#", "•", "---"]:
        clean = clean.replace(ch, "")
    clean = clean.strip()

    # Telugu voice — much better than gTTS
    voice = "te-IN-ShrutiNeural" if language == "te" else "en-IN-NeerjaNeural"

    communicate = edge_tts.Communicate(clean, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


# ─── Language detection ───────────────────────────────────────────────────────
def detect_language_from_audio(text: str) -> str:
    telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    return "telugu" if telugu_chars > 2 else "english"