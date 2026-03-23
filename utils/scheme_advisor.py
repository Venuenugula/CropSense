import json
import os
import re
import requests
from utils.gemini import call_gemini
from utils.language import get_system_prompt

KB_PATH = "rag/knowledge_base/schemes.json"

with open(KB_PATH) as f:
    SCHEMES_KB = json.load(f)

def find_relevant_schemes(crop: str = None, district: str = None) -> list:
    """Filter schemes relevant to crop and district."""
    relevant = []
    for name, data in SCHEMES_KB.items():
        crop_match = (
            not crop or
            "All crops" in data["crops"] or
            any(crop.lower() in c.lower() for c in data["crops"])
        )
        district_match = (
            not district or
            "All Telangana districts" in data["districts"] or
            any(district.lower() in d.lower() for d in data["districts"])
        )
        if crop_match and district_match:
            relevant.append((name, data))
    return relevant

def search_latest_schemes() -> str:
    """Use Gemini to search for latest farming schemes in Telangana."""
    prompt = """
Search and list the latest government schemes for farmers in Telangana, India announced in 2025-2026.
Include:
1. Any new schemes launched recently
2. Updates to existing schemes (PM-Kisan, Rythu Bandhu amounts changed?)
3. New subsidies or benefits announced

Format as a brief list with scheme name and key benefit.
Be factual and specific. If unsure about recent updates, say so.
"""
    try:
        return call_gemini(prompt)
    except Exception:
        return ""

def generate_schemes_response(
    schemes: list,
    crop: str,
    district: str,
    lang: str = "telugu",
    latest_info: str = ""
) -> str:
    """Generate comprehensive schemes response."""
    system = get_system_prompt(lang)

    schemes_text = ""
    for name, data in schemes[:5]:  # top 5 most relevant
        schemes_text += f"""
- {data['telugu_name']} ({name}):
  ప్రయోజనం: {data['benefit']}
  అర్హత: {data['eligibility']}
  దరఖాస్తు: {data['how_to_apply']}
  హెల్ప్‌లైన్: {data['helpline']}
"""

    if lang == "telugu":
        prompt = f"""
{system}

రైతు {district} జిల్లా నుండి, {crop} పంట పండిస్తున్నారు.
వారికి అందుబాటులో ఉన్న ప్రభుత్వ పథకాలు:

{schemes_text}

తాజా సమాచారం:
{latest_info if latest_info else 'అందుబాటులో లేదు'}

దయచేసి తెలుగులో సమాధానం ఇవ్వండి:

🏛️ *మీకు అందుబాటులో ఉన్న ప్రభుత్వ పథకాలు*
({district} జిల్లా, {crop} పంట)

ప్రతి పథకానికి:
- పేరు మరియు ప్రయోజనం (ఎంత డబ్బు/సహాయం)
- అర్హత
- ఎలా దరఖాస్తు చేయాలి
- హెల్ప్‌లైన్ నంబర్

చివరలో తాజా పథకాల సమాచారం కూడా చెప్పండి.
"""
    else:
        prompt = f"""
{system}

A farmer from {district} district grows {crop}.
Available government schemes:

{schemes_text}

Latest information:
{latest_info if latest_info else 'Not available'}

Reply in English:

🏛️ *Government Schemes Available for You*
({district} district, {crop} crop)

For each scheme:
- Name and benefit (exact amount/assistance)
- Eligibility
- How to apply
- Helpline number

End with latest scheme updates.
"""
    return call_gemini(prompt)