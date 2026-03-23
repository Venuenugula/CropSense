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
from utils.observability import Timer, log_event
from PIL import Image, ImageStat
import io

MIN_CONFIDENCE_PERCENT = 55.0
MIN_BRIGHTNESS = 35.0
MIN_SHARPNESS_VAR = 20.0


def _assess_photo_quality(image: Image.Image) -> dict:
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    brightness = stat.mean[0]
    sharpness_var = stat.var[0]
    is_dark = brightness < MIN_BRIGHTNESS
    is_blurry = sharpness_var < MIN_SHARPNESS_VAR
    return {
        "ok": not (is_dark or is_blurry),
        "brightness": round(brightness, 2),
        "sharpness_var": round(sharpness_var, 2),
        "is_dark": is_dark,
        "is_blurry": is_blurry,
    }

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
    timer = Timer()
    # Step 1 — Disease detection
    image        = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    quality = _assess_photo_quality(image)
    if not quality["ok"]:
        response = (
            "⚠️ *ఫోటో క్లారిటీ తక్కువగా ఉంది.*\n\n"
            "దయచేసి ఇలా మళ్లీ ఫోటో పంపండి:\n"
            "1) వెలుతురు బాగా ఉండాలి\n"
            "2) ఆకు దగ్గరగా, ఫోకస్‌లో ఉండాలి\n"
            "3) చేతి కదలిక లేకుండా తీసండి"
            if lang == "telugu" else
            "⚠️ *Photo quality is too low for reliable detection.*\n\n"
            "Please retake with:\n"
            "1) good lighting\n"
            "2) close-up focus on one leaf\n"
            "3) steady hand (no blur)"
        )
        location_name = get_location_name(lat, lon)
        weather_risk = {"risk_level": "Unknown", "risk_score": 0.0}
        log_event(
            "photo_quality_low",
            user_id=user_id,
            brightness=quality["brightness"],
            sharpness_var=quality["sharpness_var"],
            pipeline_ms=timer.elapsed_ms(),
        )
        return {
            "disease_key": "image_quality_issue",
            "confidence": 0.0,
            "is_healthy": False,
            "top_predictions": [],
            "weather_risk": weather_risk,
            "location_name": location_name,
            "response": response,
            "lang": lang,
            "uncertain": True,
        }
    predictions  = predict(image, top_k=3)
    top          = predictions[0]
    disease_key  = top["disease"]
    confidence   = top["confidence"]
    is_healthy   = "healthy" in disease_key.lower()
    crop_name    = disease_key.split("___")[0].replace("_", " ")
    uncertain    = confidence < MIN_CONFIDENCE_PERCENT

    # Step 2 — Weather + spread risk
    forecast      = get_forecast(lat, lon)
    weather_risk  = predict_spread_risk(disease_key, forecast)
    location_name = get_location_name(lat, lon)

    # Step 3 — LLM response
    if uncertain:
        if lang == "telugu":
            response = (
                "⚠️ *చిత్రం స్పష్టంగా లేదు కాబట్టి ఖచ్చితంగా చెప్పలేకపోతున్నాం.*\n\n"
                "దయచేసి మళ్లీ ఫోటో తీసి పంపండి:\n"
                "1) పగటి వెలుతురులో తీసండి\n"
                "2) ఆకు దగ్గరగా మరియు ఫోకస్‌లో ఉండాలి\n"
                "3) ఒకే ఆకును స్పష్టంగా చూపండి\n"
                "4) బ్లర్ కాకుండా చేతిని స్థిరంగా ఉంచండి"
            )
        else:
            response = (
                "⚠️ *The image is unclear, so confidence is low.*\n\n"
                "Please retake and send a clearer photo:\n"
                "1) Use daylight\n"
                "2) Keep the leaf close and in focus\n"
                "3) Capture one affected leaf clearly\n"
                "4) Avoid blur by holding phone steady"
            )
    elif is_healthy:
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
    log_event(
        "pipeline_completed",
        user_id=user_id,
        disease_key=disease_key,
        confidence=confidence,
        uncertain=uncertain,
        risk_level=weather_risk.get("risk_level", "Unknown"),
        pipeline_ms=timer.elapsed_ms(),
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
        "uncertain":       uncertain,
    }