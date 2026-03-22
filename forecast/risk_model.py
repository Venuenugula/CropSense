import numpy as np

# Disease-specific weather risk thresholds
# Based on plant pathology research for each disease type
DISEASE_RISK_PROFILES = {
    "fungal": {
        "high_humidity_threshold":   80,
        "optimal_temp_min":          15,
        "optimal_temp_max":          30,
        "rain_threshold_mm":          5,
        "description": "Fungal diseases spread rapidly in humid, wet conditions"
    },
    "bacterial": {
        "high_humidity_threshold":   75,
        "optimal_temp_min":          20,
        "optimal_temp_max":          32,
        "rain_threshold_mm":          3,
        "description": "Bacterial diseases spread through rain splash and wounds"
    },
    "viral": {
        "high_humidity_threshold":   60,
        "optimal_temp_min":          25,
        "optimal_temp_max":          35,
        "rain_threshold_mm":          0,
        "description": "Viral diseases spread via insect vectors (whitefly, aphids)"
    },
    "mite": {
        "high_humidity_threshold":   40,
        "optimal_temp_min":          28,
        "optimal_temp_max":          40,
        "rain_threshold_mm":          0,
        "description": "Spider mites thrive in hot dry conditions"
    },
}

DISEASE_CATEGORIES = {
    "Tomato___Late_blight":                              "fungal",
    "Tomato___Early_blight":                             "fungal",
    "Tomato___Septoria_leaf_spot":                       "fungal",
    "Tomato___Leaf_Mold":                                "fungal",
    "Tomato___Target_Spot":                              "fungal",
    "Tomato___Bacterial_spot":                           "bacterial",
    "Tomato___Tomato_mosaic_virus":                      "viral",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus":            "viral",
    "Tomato___Spider_mites Two-spotted_spider_mite":     "mite",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot":"fungal",
    "Corn_(maize)___Common_rust_":                       "fungal",
    "Corn_(maize)___Northern_Leaf_Blight":               "fungal",
    "Potato___Late_blight":                              "fungal",
    "Potato___Early_blight":                             "fungal",
    "Grape___Black_rot":                                 "fungal",
    "Grape___Esca_(Black_Measles)":                      "fungal",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)":        "fungal",
    "Apple___Apple_scab":                                "fungal",
    "Apple___Black_rot":                                 "fungal",
    "Apple___Cedar_apple_rust":                          "fungal",
    "Peach___Bacterial_spot":                            "bacterial",
    "Pepper,_bell___Bacterial_spot":                     "bacterial",
}

def _day_risk_score(day: dict, profile: dict) -> float:
    """Score 0-1 for how favourable a single day's weather is for disease spread."""
    score = 0.0
    humidity = day["avg_humidity"]
    temp     = day["avg_temp"]
    rain     = day["total_rain"]

    # Humidity contribution (0-0.4)
    if humidity >= profile["high_humidity_threshold"]:
        score += 0.4 * min(1.0,
            (humidity - profile["high_humidity_threshold"]) / 20 + 0.5)

    # Temperature contribution (0-0.3)
    t_min = profile["optimal_temp_min"]
    t_max = profile["optimal_temp_max"]
    if t_min <= temp <= t_max:
        # Peak risk at midpoint of range
        mid   = (t_min + t_max) / 2
        score += 0.3 * (1 - abs(temp - mid) / ((t_max - t_min) / 2))

    # Rain contribution (0-0.3) — not applicable for mites/viral
    if rain >= profile["rain_threshold_mm"] and profile["rain_threshold_mm"] > 0:
        score += 0.3 * min(1.0, rain / 20)

    return min(score, 1.0)

def predict_spread_risk(disease_key: str, forecast: list[dict]) -> dict:
    """
    Predict 7-day disease spread risk.
    Returns risk_level, score, reason, and daily breakdown.
    """
    category = DISEASE_CATEGORIES.get(disease_key, "fungal")
    profile  = DISEASE_RISK_PROFILES[category]
    is_healthy = "healthy" in disease_key.lower()

    if is_healthy:
        return {
            "risk_level": "Low",
            "risk_score": 0.0,
            "category":   category,
            "reason":     "No disease detected — maintain regular monitoring.",
            "daily":      [],
            "advice":     "Continue regular field scouting every 7 days."
        }

    daily_scores = []
    daily_breakdown = []
    for day in forecast[:7]:
        score = _day_risk_score(day, profile)
        daily_scores.append(score)
        daily_breakdown.append({
            "date":       day["date"],
            "risk_score": round(score, 2),
            "temp":       day["avg_temp"],
            "humidity":   day["avg_humidity"],
            "rain":       day["total_rain"],
        })

    avg_score  = sum(daily_scores) / len(daily_scores) if daily_scores else 0
    peak_score = max(daily_scores) if daily_scores else 0
    final_score = (avg_score * 0.6) + (peak_score * 0.4)

    # Determine risk level
    if final_score >= 0.65:
        risk_level = "High"
        advice     = ("వెంటనే పిచికారీ చేయండి — ఆలస్యం చేయవద్దు! "
                      "Spray fungicide immediately — do not delay!")
    elif final_score >= 0.35:
        risk_level = "Medium"
        advice     = ("జాగ్రత్తగా ఉండండి — రేపు పిచికారీ చేయడం మంచిది. "
                      "Stay alert — spray within 2 days.")
    else:
        risk_level = "Low"
        advice     = ("ఈ వారం వ్యాప్తి ప్రమాదం తక్కువ. "
                      "Low spread risk this week — monitor regularly.")

    # Build reason string
    avg_humidity = sum(d["avg_humidity"] for d in forecast[:7]) / 7
    avg_temp     = sum(d["avg_temp"] for d in forecast[:7]) / 7
    total_rain   = sum(d["total_rain"] for d in forecast[:7])

    reason = (
        f"{profile['description']}. "
        f"Next 7 days: avg temp {avg_temp:.1f}°C, "
        f"avg humidity {avg_humidity:.0f}%, "
        f"total rain {total_rain:.1f}mm."
    )

    return {
        "risk_level":  risk_level,
        "risk_score":  round(final_score, 2),
        "category":    category,
        "reason":      reason,
        "advice":      advice,
        "daily":       daily_breakdown,
    }


if __name__ == "__main__":
    # Test with mock forecast data
    mock_forecast = [
        {"date": f"2025-03-{20+i}", "avg_temp": 22 + i,
         "avg_humidity": 85 + i, "total_rain": 8.0, "description": "rain"}
        for i in range(7)
    ]
    result = predict_spread_risk("Tomato___Late_blight", mock_forecast)
    print(f"Risk level: {result['risk_level']}")
    print(f"Risk score: {result['risk_score']}")
    print(f"Reason: {result['reason']}")
    print(f"Advice: {result['advice']}")
    for day in result["daily"]:
        print(f"  {day['date']}: score={day['risk_score']} "
              f"temp={day['temp']}°C humidity={day['humidity']}%")