import requests
import json
from datetime import datetime, timedelta

# Agmarknet API — free government API for mandi prices
AGMARK_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
API_KEY    = "579b464db66ec23bdd000001cdd3946e44ce4aad38d976a3e1ec943"  # public demo key

TELUGU_CROP_MAP = {
    "వరి": "Paddy(Dhan)(Common)",
    "rice": "Paddy(Dhan)(Common)",
    "paddy": "Paddy(Dhan)(Common)",
    "టమాటో": "Tomato",
    "tomato": "Tomato",
    "మొక్కజొన్న": "Maize",
    "maize": "Maize",
    "corn": "Maize",
    "పత్తి": "Cotton",
    "cotton": "Cotton",
    "వేరుశెనగ": "Groundnut",
    "groundnut": "Groundnut",
    "ఉల్లి": "Onion",
    "onion": "Onion",
    "మిరపకాయ": "Chilli",
    "chilli": "Chilli",
    "బంగాళాదుంప": "Potato",
    "potato": "Potato",
}

TELANGANA_MANDIS = [
    "Warangal", "Nizamabad", "Karimnagar", "Khammam",
    "Nalgonda", "Mahbubnagar", "Adilabad", "Hyderabad",
    "Suryapet", "Siddipet", "Mancherial", "Jagtial"
]

def find_crop_name(query: str) -> str:
    """Map Telugu/English crop name to Agmarknet name."""
    q = query.lower().strip()
    for alias, api_name in TELUGU_CROP_MAP.items():
        if alias.lower() in q or q in alias.lower():
            return api_name
    return query.title()

def fetch_mandi_prices(crop_query: str, state: str = "Telangana") -> list:
    """Fetch live mandi prices from Agmarknet API."""
    crop_name = find_crop_name(crop_query)
    today     = datetime.now().strftime("%d/%m/%Y")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

    for date in [today, yesterday]:
        try:
            params = {
                "api-key": API_KEY,
                "format":  "json",
                "limit":   50,
                "filters[State]":     state,
                "filters[Commodity]": crop_name,
                "filters[Arrival_Date]": date,
            }
            resp = requests.get(AGMARK_URL, params=params, timeout=10)
            data = resp.json()

            if data.get("records"):
                return data["records"], date, crop_name

        except Exception as e:
            print(f"Agmarknet API error: {e}")

    return [], today, crop_name

def format_price_response(
    records: list,
    crop_query: str,
    crop_name: str,
    date: str,
    lang: str = "telugu"
) -> str:
    """Format mandi price response."""
    telugu_crop = crop_query

    if not records:
        # Fallback — use approximate prices from KB
        return _fallback_prices(crop_query, lang)

    # Sort by modal price descending
    records = sorted(records, key=lambda x: float(x.get("Modal_Price", 0)), reverse=True)

    if lang == "telugu":
        response = f"💰 <b>{telugu_crop} మండి ధరలు</b> ({date})\n\n"
        for r in records[:8]:
            mandi   = r.get("Market", "")
            dist    = r.get("District", "")
            min_p   = r.get("Min_Price", "N/A")
            max_p   = r.get("Max_Price", "N/A")
            modal_p = r.get("Modal_Price", "N/A")
            response += (
                f"🏪 <b>{mandi}</b> ({dist})\n"
                f"   కనిష్ట ధర: ₹{min_p}/క్వింటల్\n"
                f"   గరిష్ట ధర: ₹{max_p}/క్వింటల్\n"
                f"   సాధారణ ధర: ₹{modal_p}/క్వింటల్\n\n"
            )
        response += "💡 మీ దగ్గరి మండికి వెళ్ళే ముందు ధర నిర్ధారించుకోండి."
    else:
        response = f"💰 <b>{crop_name} Mandi Prices</b> ({date})\n\n"
        for r in records[:8]:
            mandi   = r.get("Market", "")
            dist    = r.get("District", "")
            min_p   = r.get("Min_Price", "N/A")
            max_p   = r.get("Max_Price", "N/A")
            modal_p = r.get("Modal_Price", "N/A")
            response += (
                f"🏪 <b>{mandi}</b> ({dist})\n"
                f"   Min: ₹{min_p}/quintal\n"
                f"   Max: ₹{max_p}/quintal\n"
                f"   Modal: ₹{modal_p}/quintal\n\n"
            )
        response += "💡 Verify prices at your local mandi before selling."

    return response

def _fallback_prices(crop_query: str, lang: str) -> str:
    """Fallback when API is unavailable."""
    if lang == "telugu":
        return (
            f"⚠️ ప్రస్తుతం {crop_query} ధరల సమాచారం అందుబాటులో లేదు.\n\n"
            f"దయచేసి నేరుగా మీ స్థానిక మండి సంప్రదించండి:\n"
            f"• వరంగల్ మండి: 0870-2578901\n"
            f"• కరీంనగర్ మండి: 0878-2234567\n"
            f"• నిజామాబాద్ మండి: 08462-225678\n\n"
            f"లేదా Agmarknet వెబ్‌సైట్ చూడండి:\n"
            f"agmarknet.gov.in"
        )
    else:
        return (
            f"⚠️ Live prices for {crop_query} unavailable right now.\n\n"
            f"Please check:\n"
            f"• agmarknet.gov.in\n"
            f"• Or call your local mandi directly."
        )