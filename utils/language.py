SUPPORTED = {"telugu": "te", "english": "en"}
DEFAULT   = "telugu"

TELUGU_SYSTEM = """మీరు రైతులకు సహాయం చేసే వ్యవసాయ నిపుణుడు.
సులభమైన తెలుగులో సమాధానం ఇవ్వండి. వైద్య పరిభాష వాడకండి.
రైతు అర్థం చేసుకునే విధంగా మాట్లాడండి."""

ENGLISH_SYSTEM = """You are an agricultural expert helping farmers.
Reply in simple, clear English. Avoid technical jargon.
Speak like you are talking directly to a farmer."""

def get_system_prompt(lang: str) -> str:
    return TELUGU_SYSTEM if lang == "telugu" else ENGLISH_SYSTEM

def detect_language(text: str) -> str:
    """Detect if user typed in Telugu script."""
    telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    return "telugu" if telugu_chars > 2 else "english"