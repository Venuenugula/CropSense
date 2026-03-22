import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5"

def get_current_weather(lat: float, lon: float) -> dict:
    """Get current weather for a location."""
    url = f"{BASE_URL}/weather"
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

def get_forecast(lat: float, lon: float, days: int = 7) -> list[dict]:
    """Get 7-day hourly forecast and aggregate to daily summaries."""
    url = f"{BASE_URL}/forecast"
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

    # Aggregate to daily
    from collections import defaultdict
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
            "date":        date,
            "avg_temp":    round(sum(d["temps"])      / len(d["temps"]), 1),
            "avg_humidity":round(sum(d["humidities"]) / len(d["humidities"]), 1),
            "total_rain":  round(d["rain"], 1),
            "description": max(set(d["descriptions"]),
                               key=d["descriptions"].count),
        })
    return result

def get_location_name(lat: float, lon: float) -> str:
    """Reverse geocode lat/lon to city name."""
    url = "http://api.openweathermap.org/geo/1.0/reverse"
    params = {"lat": lat, "lon": lon, "limit": 1, "appid": API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data:
            return f"{data[0].get('name', '')}, {data[0].get('state', '')}"
    except Exception:
        pass
    return f"{lat:.2f}°N, {lon:.2f}°E"