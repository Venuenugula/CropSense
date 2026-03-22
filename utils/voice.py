import os
import io
import tempfile
from groq import Groq
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_bytes: bytes, language: str = "te") -> str:
    """
    Convert farmer's voice message to text using Groq Whisper.
    language: 'te' for Telugu, 'en' for English
    """
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language=language,
                response_format="text"
            )
        return transcription.strip()
    finally:
        os.unlink(tmp_path)


def text_to_speech(text: str, language: str = "te") -> bytes:
    """
    Convert text response to audio using gTTS.
    Returns audio bytes to send back via Telegram.
    language: 'te' for Telugu, 'en' for English
    """
    # Clean text for TTS — remove markdown symbols
    clean = text
    for ch in ["*", "_", "`", "#", "•", "🌾", "💊", "🛡️", "⛅",
               "🔍", "✅", "❌", "⚠️", "📸", "📍"]:
        clean = clean.replace(ch, "")
    clean = clean.replace("---", "").strip()

    tts  = gTTS(text=clean, lang=language, slow=False)
    buf  = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def detect_language_from_audio(text: str) -> str:
    """Detect if transcribed text is Telugu or English."""
    telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    return "telugu" if telugu_chars > 2 else "english"