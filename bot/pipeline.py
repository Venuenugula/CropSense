import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.inference import predict
from rag.retriever import retrieve_treatment
from forecast.weather import get_forecast, get_location_name
from forecast.risk_model import predict_spread_risk
from utils.response_generator import (
    generate_disease_response,
    generate_healthy_response,
)
from db.models import log_detection, init_db
from PIL import Image
import io

# init DB on startup
try:
    init_db()
except Exception as e:
    print(f"DB init skipped: {e}")

def run_pipeline(
    image_bytes: bytes,
    lat: float,
    lon: float,
    lang: str = "telugu",
    user_id: int = 0,
) -> dict:
    # Step 1 — Disease detection
    image        = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    predictions  = predict(image, top_k=3)
    top          = predictions[0]
    disease_key  = top["disease"]
    confidence   = top["confidence"]
    is_healthy   = "healthy" in disease_key.lower()
    crop_name    = disease_key.split("___")[0].replace("_", " ")

    # Step 2 — Weather + spread risk
    forecast      = get_forecast(lat, lon)
    weather_risk  = predict_spread_risk(disease_key, forecast)
    location_name = get_location_name(lat, lon)

    # Step 3 — LLM response
    if is_healthy:
        response = generate_healthy_response(crop_name, confidence, lang)
    else:
        response = generate_disease_response(
            disease_key, confidence, weather_risk, lang
        )

    # Step 4 — Log to database
    log_detection(
        user_id=user_id,
        disease_key=disease_key,
        crop=crop_name,
        confidence=confidence,
        is_healthy=is_healthy,
        risk_level=weather_risk.get("risk_level", "Unknown"),
        risk_score=weather_risk.get("risk_score", 0.0),
        lat=lat,
        lon=lon,
        location_name=location_name,
        lang=lang,
    )

    return {
        "disease_key":     disease_key,
        "confidence":      confidence,
        "is_healthy":      is_healthy,
        "top_predictions": predictions,
        "weather_risk":    weather_risk,
        "location_name":   location_name,
        "response":        response,
        "lang":            lang,
    }