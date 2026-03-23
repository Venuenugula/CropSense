import json
from utils.gemini import call_gemini
from utils.language import get_system_prompt
from datetime import datetime

KB_PATH = "rag/knowledge_base/crop_calendar.json"

with open(KB_PATH) as f:
    CALENDAR_KB = json.load(f)

CROP_ALIASES = {
    "వరి": "Rice", "rice": "Rice", "paddy": "Rice",
    "టమాటో": "Tomato", "tomato": "Tomato",
    "మొక్కజొన్న": "Maize", "maize": "Maize", "corn": "Maize",
    "పత్తి": "Cotton", "cotton": "Cotton",
    "వేరుశెనగ": "Groundnut", "groundnut": "Groundnut",
    "peanut": "Groundnut", "వేరుశనగ": "Groundnut",
}

def find_crop(query: str) -> tuple:
    """Find crop in KB. Returns (english_name, data) or (None, None)."""
    q = query.lower().strip()
    for alias, english in CROP_ALIASES.items():
        if alias.lower() in q or q in alias.lower():
            return english, CALENDAR_KB.get(english)
    for name, data in CALENDAR_KB.items():
        if name.lower() in q or q in name.lower():
            return name, data
    return None, None

def get_current_month_advice(crop_name: str, data: dict, season: str = None) -> dict:
    """Get advice for current month."""
    current_month = datetime.now().strftime("%B")
    seasons       = data.get("seasons", {})

    if not season:
        # Pick season based on current month
        kharif_months = ["June","July","August","September","October","November"]
        season = "Kharif" if current_month in kharif_months else "Rabi"
        if season not in seasons:
            season = list(seasons.keys())[0]

    season_data    = seasons.get(season, {})
    schedule       = season_data.get("schedule", {})
    current_advice = schedule.get(current_month, {})

    return {
        "crop":          crop_name,
        "season":        season,
        "current_month": current_month,
        "advice":        current_advice,
        "sowing":        season_data.get("sowing_months"),
        "harvest":       season_data.get("harvest_months"),
        "duration":      season_data.get("duration_days"),
        "full_schedule": schedule,
    }

def generate_calendar_response(
    crop_name: str,
    data: dict,
    lang: str = "telugu",
    show_full: bool = False
) -> str:
    """Generate calendar response using Gemini."""
    system      = get_system_prompt(lang)
    info        = get_current_month_advice(crop_name, data)
    telugu_name = data.get("telugu_name", crop_name)

    # Build schedule summary
    schedule_text = ""
    for month, details in info["full_schedule"].items():
        schedule_text += f"\n{month}:\n"
        schedule_text += f"  కార్యక్రమాలు/Activities: {', '.join(details.get('activities', []))}\n"
        schedule_text += f"  ఎరువులు/Fertilizer: {details.get('fertilizer', 'None')}\n"
        schedule_text += f"  నీటి తడి/Irrigation: {details.get('irrigation', '')}\n"
        schedule_text += f"  పర్యవేక్షణ/Scouting: {details.get('scouting', '')}\n"

    if lang == "telugu":
        prompt = f"""
{system}

{telugu_name} ({crop_name}) పంట క్యాలెండర్ — {info['season']} సీజన్

సీజన్ వివరాలు:
- విత్తనం వేసే సమయం: {info['sowing']}
- పంట కోత సమయం: {info['harvest']}
- పంట వ్యవధి: {info['duration']} రోజులు
- ప్రస్తుత నెల: {info['current_month']}

ప్రస్తుత నెల ({info['current_month']}) చేయాల్సిన పనులు:
- కార్యక్రమాలు: {', '.join(info['advice'].get('activities', ['No specific activities']))}
- ఎరువులు: {info['advice'].get('fertilizer', 'None')}
- నీటి తడి: {info['advice'].get('irrigation', '')}
- పర్యవేక్షణ: {info['advice'].get('scouting', '')}

నెల వారీ పూర్తి షెడ్యూల్:
{schedule_text}

దయచేసి తెలుగులో ఈ format లో సమాధానం ఇవ్వండి:

🌾 *{telugu_name} పంట క్యాలెండర్ ({info['season']})*

📅 *సీజన్ సమాచారం:*
విత్తు నుండి కోత వరకు స్పష్టంగా చెప్పండి.

🗓️ *ఈ నెల ({info['current_month']}) చేయాల్సినవి:*
ఈ నెలలో రైతు చేయాల్సిన ముఖ్యమైన పనులు చెప్పండి.

📆 *నెల వారీ పూర్తి కార్యక్రమం:*
ప్రతి నెలకు 2-3 ముఖ్యమైన పనులు సులభంగా చెప్పండి.

💡 *ముఖ్యమైన చిట్కాలు:*
2-3 ముఖ్యమైన సూచనలు ఇవ్వండి.
"""
    else:
        prompt = f"""
{system}

{crop_name} Crop Calendar — {info['season']} Season

Season details:
- Sowing: {info['sowing']}
- Harvest: {info['harvest']}
- Duration: {info['duration']} days
- Current month: {info['current_month']}

Current month ({info['current_month']}) activities:
- Activities: {', '.join(info['advice'].get('activities', ['None']))}
- Fertilizer: {info['advice'].get('fertilizer', 'None')}
- Irrigation: {info['advice'].get('irrigation', '')}
- Scouting: {info['advice'].get('scouting', '')}

Full monthly schedule:
{schedule_text}

Reply in this format:

🌾 *{crop_name} Crop Calendar ({info['season']})*

📅 *Season Overview:*
Clear sowing to harvest timeline.

🗓️ *This Month ({info['current_month']}) — What to do now:*
Key activities for the farmer right now.

📆 *Monthly Schedule:*
2-3 key activities per month, simple language.

💡 *Important Tips:*
2-3 key advisory points.
"""
    return call_gemini(prompt)

def get_available_crops() -> str:
    """List all crops in the knowledge base."""
    crops = []
    for name, data in CALENDAR_KB.items():
        crops.append(f"{data['telugu_name']} ({name})")
    return ", ".join(crops)