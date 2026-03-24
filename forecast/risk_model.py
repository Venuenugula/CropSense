import logging
import os

import numpy as np

from forecast.risk_model_ml import ml_model_available

logger = logging.getLogger(__name__)

# Disease-specific weather risk thresholds
# Based on plant pathology research for each disease type
DISEASE_RISK_PROFILES = {
    "fungal": {
        "high_humidity_threshold":   80,
        "optimal_temp_min":          15,
        "optimal_temp_max":          30,
        "rain_threshold_mm":          5,
        "description": "Fungal diseases spread rapidly in humid, wet conditions",
    },
    "bacterial": {
        "high_humidity_threshold":   75,
        "optimal_temp_min":          20,
        "optimal_temp_max":          32,
        "rain_threshold_mm":          3,
        "description": "Bacterial diseases spread through rain splash and wounds",
    },
    "viral": {
        "high_humidity_threshold":   60,
        "optimal_temp_min":          25,
        "optimal_temp_max":          35,
        "rain_threshold_mm":          0,
        "description": "Viral diseases spread via insect vectors (whitefly, aphids)",
    },
    "mite": {
        "high_humidity_threshold":   40,
        "optimal_temp_min":          28,
        "optimal_temp_max":          40,
        "rain_threshold_mm":          0,
        "description": "Spider mites thrive in hot dry conditions",
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

    if humidity >= profile["high_humidity_threshold"]:
        score += 0.4 * min(1.0,
            (humidity - profile["high_humidity_threshold"]) / 20 + 0.5)

    t_min = profile["optimal_temp_min"]
    t_max = profile["optimal_temp_max"]
    if t_min <= temp <= t_max:
        mid   = (t_min + t_max) / 2
        score += 0.3 * (1 - abs(temp - mid) / ((t_max - t_min) / 2))

    if rain >= profile["rain_threshold_mm"] and profile["rain_threshold_mm"] > 0:
        score += 0.3 * min(1.0, rain / 20)

    return min(score, 1.0)


def _advice_for_risk_level(risk_level: str) -> str:
    if risk_level == "High":
        return ("వెంటనే పిచికారీ చేయండి — ఆలస్యం చేయవద్దు! "
                "Spray fungicide immediately — do not delay!")
    if risk_level == "Medium":
        return ("జాగ్రత్తగా ఉండండి — రేపు పిచికారీ చేయడం మంచిది. "
                "Stay alert — spray within 2 days.")
    return ("ఈ వారం వ్యాప్తి ప్రమాదం తక్కువ. "
            "Low spread risk this week — monitor regularly.")


def _predict_spread_risk_rules(
    disease_key: str,
    forecast: list[dict],
    category: str,
    profile: dict,
) -> dict:
    """Rule-based 7-day score + daily breakdown (disease-specific physics)."""
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

    if final_score >= 0.65:
        risk_level = "High"
    elif final_score >= 0.35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

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
        "advice":      _advice_for_risk_level(risk_level),
        "daily":       daily_breakdown,
    }


def _use_ml_spread_risk() -> bool:
    return os.getenv("USE_ML_SPREAD_RISK", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def predict_spread_risk(disease_key: str, forecast: list[dict]) -> dict:
    """
    Predict 7-day disease spread risk.

    Uses **hybrid** logic: if ``forecast/risk_model.pkl`` exists and
    ``USE_ML_SPREAD_RISK`` is enabled, headline ``risk_level`` / ``risk_score``
    come from an XGBoost model trained on Meteostat history; disease-specific
    **daily** breakdown still comes from rules for explainability.

    Falls back to pure rule-based scoring if ML is unavailable or errors.
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
            "advice":     "Continue regular field scouting every 7 days.",
            "risk_source": "n/a",
        }

    rules = _predict_spread_risk_rules(disease_key, forecast, category, profile)
    rules["risk_source"] = "rules"

    if not _use_ml_spread_risk() or not ml_model_available():
        return rules

    try:
        from forecast.risk_model_ml import predict_risk_level_and_score

        ml_level, ml_score, proba = predict_risk_level_and_score(forecast)
        avg_humidity = sum(d["avg_humidity"] for d in forecast[:7]) / 7
        avg_temp     = sum(d["avg_temp"] for d in forecast[:7]) / 7
        total_rain   = sum(d["total_rain"] for d in forecast[:7])

        reason = (
            f"{profile['description']} "
            f"ML weather ensemble: {ml_level} (score {ml_score:.2f}; "
            f"p={np.round(proba, 2).tolist()}). "
            f"Next 7 days: avg temp {avg_temp:.1f}°C, "
            f"avg humidity {avg_humidity:.0f}%, total rain {total_rain:.1f}mm."
        )

        return {
            "risk_level":  ml_level,
            "risk_score":  round(float(ml_score), 2),
            "category":    category,
            "reason":      reason,
            "advice":      _advice_for_risk_level(ml_level),
            "daily":       rules["daily"],
            "risk_source": "ml",
        }
    except Exception as e:
        logger.warning("ML spread risk unavailable, using rules: %s", e)
        return rules


if __name__ == "__main__":
    mock_forecast = [
        {"date": f"2025-03-{20+i}", "avg_temp": 22 + i,
         "avg_humidity": 85 + i, "total_rain": 8.0, "description": "rain"}
        for i in range(7)
    ]
    result = predict_spread_risk("Tomato___Late_blight", mock_forecast)
    print(f"Risk level: {result['risk_level']} ({result.get('risk_source')})")
    print(f"Risk score: {result['risk_score']}")
    print(f"Reason: {result['reason']}")
    print(f"Advice: {result['advice']}")
    for day in result["daily"]:
        print(f"  {day['date']}: score={day['risk_score']} "
              f"temp={day['temp']}°C humidity={day['humidity']}%")
