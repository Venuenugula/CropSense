import requests
import os
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5"

# ─── Telangana district coordinates ─────────────────────────────────────────
TELANGANA_DISTRICTS = {
    "నిజామాబాద్":   (18.6725, 78.0941),
    "ఆదిలాబాద్":    (19.6641, 78.5320),
    "కరీంనగర్":     (18.4386, 79.1288),
    "వరంగల్":       (17.9784, 79.5941),
    "నల్లగొండ":     (17.0575, 79.2690),
    "మహబూబ్‌నగర్":  (16.7376, 77.9864),
    "హైదరాబాద్":    (17.3850, 78.4867),
    "బాసర":         (18.9543, 79.1320),
    "సిద్దిపేట":    (18.1018, 78.8520),
    "నిర్మల్":      (19.0948, 78.3440),
    "జగిత్యాల":     (18.7950, 78.9170),
    "పెద్దపల్లి":   (18.6140, 79.3760),
    "nizamabad":    (18.6725, 78.0941),
    "adilabad":     (19.6641, 78.5320),
    "karimnagar":   (18.4386, 79.1288),
    "warangal":     (17.9784, 79.5941),
    "nalgonda":     (17.0575, 79.2690),
    "mahbubnagar":  (16.7376, 77.9864),
    "hyderabad":    (17.3850, 78.4867),
    "basar":        (18.9543, 79.1320),
    "siddipet":     (18.1018, 78.8520),
    "nirmal":       (19.0948, 78.3440),
    "jagtial":      (18.7950, 78.9170),
    "peddapalli":   (18.6140, 79.3760),
    "mancherial":   (18.8706, 79.4559),
    "rajanna":      (18.4497, 79.4951),
    "bhadradri":    (17.5789, 80.8910),
    "khammam":      (17.2473, 80.1514),
    "suryapet":     (17.1391, 79.6218),
    "yadadri":      (17.2740, 78.9710),
    "medchal":      (17.6290, 78.4810),
    "rangareddy":   (17.3617, 78.3850),
    "vikarabad":    (17.3350, 77.9040),
    "sangareddy":   (17.6234, 77.9925),
    "medak":        (18.0530, 78.2617),
    "kamareddy":    (18.3220, 78.3420),
    "nagarkurnool": (16.4833, 78.3167),
    "wanaparthy":   (16.3650, 78.0600),
    "gadwal":       (16.2333, 77.8000),
    "jogulamba":    (16.2333, 77.8000),
    "narayanpet":   (16.7456, 77.4958),
    "mahabubabad":  (17.5981, 80.0012),
    "mulugu":       (18.1953, 80.0664),
    "bhupalapally": (18.4443, 79.8564),
    "jayashankar":  (18.4443, 79.8564),
    "kumuram bheem":(19.2889, 79.5467),
    "asifabad":     (19.3700, 79.2800),
}

DEFAULT_LAT = 17.3850
DEFAULT_LON = 78.4867  # Hyderabad fallback

# ─── Location resolution ─────────────────────────────────────────────────────
def resolve_location(text: str = None) -> tuple:
    """
    Resolve a district name (Telugu or English) to (lat, lon).
    Falls back to Hyderabad if not found.
    """
    if not text:
        return DEFAULT_LAT, DEFAULT_LON

    key = text.strip().lower()
    for district, coords in TELANGANA_DISTRICTS.items():
        if key in district.lower() or district.lower() in key:
            return coords

    return DEFAULT_LAT, DEFAULT_LON

# ─── Weather API calls ───────────────────────────────────────────────────────
def get_current_weather(lat: float, lon: float) -> dict:
    """Get current weather conditions for a GPS location."""
    url    = f"{BASE_URL}/weather"
    params = {
        "lat":   lat,
        "lon":   lon,
        "appid": API_KEY,
        "units": "metric",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "temp":        data["main"]["temp"],
        "humidity":    data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "wind_speed":  data["wind"]["speed"],
        "rain_mm":     data.get("rain", {}).get("1h", 0.0),
    }

def get_forecast(lat: float, lon: float, days: int = 7) -> list:
    """
    Get 7-day forecast aggregated to daily summaries.
    Uses real GPS coordinates — from farmer's phone or district lookup.
    """
    url    = f"{BASE_URL}/forecast"
    params = {
        "lat":   lat,
        "lon":   lon,
        "appid": API_KEY,
        "units": "metric",
        "cnt":   days * 8,  # 8 readings per day (every 3h)
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json()["list"]

    daily = defaultdict(lambda: {
        "temps": [], "humidities": [], "rain": 0.0, "descriptions": []
    })
    for item in items:
        date = item["dt_txt"].split(" ")[0]
        daily[date]["temps"].append(item["main"]["temp"])
        daily[date]["humidities"].append(item["main"]["humidity"])
        daily[date]["rain"] += item.get("rain", {}).get("3h", 0.0)
        daily[date]["descriptions"].append(item["weather"][0]["description"])

    result = []
    for date, d in list(daily.items())[:days]:
        result.append({
            "date":         date,
            "avg_temp":     round(sum(d["temps"])       / len(d["temps"]), 1),
            "avg_humidity": round(sum(d["humidities"])  / len(d["humidities"]), 1),
            "total_rain":   round(d["rain"], 1),
            "description":  max(set(d["descriptions"]),
                                key=d["descriptions"].count),
        })
    return result

def get_location_name(lat: float, lon: float) -> str:
    """
    Reverse geocode GPS coordinates to a human-readable location name.
    Falls back to known Telangana locations, then to coordinate string.
    """
    url    = "http://api.openweathermap.org/geo/1.0/reverse"
    params = {"lat": lat, "lon": lon, "limit": 1, "appid": API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            name  = data[0].get("name", "")
            state = data[0].get("state", "")
            return f"{name}, {state}" if state else name
    except Exception:
        pass

    # Fallback — match known Telangana districts by proximity
    for district, (dlat, dlon) in TELANGANA_DISTRICTS.items():
        if abs(lat - dlat) < 0.15 and abs(lon - dlon) < 0.15:
            # Return English name only
            if not any('\u0C00' <= c <= '\u0C7F' for c in district):
                return f"{district.title()}, Telangana"

    return f"{lat:.4f}°N, {lon:.4f}°E"


if __name__ == "__main__":
    # Test resolve_location
    print("Testing location resolution:")
    tests = ["basar", "వరంగల్", "karimnagar", "xyz_unknown"]
    for t in tests:
        lat, lon = resolve_location(t)
        print(f"  '{t}' → ({lat}, {lon})")

    print("\nTesting get_location_name with Basar coords:")
    print(" ", get_location_name(18.9543, 79.1320))