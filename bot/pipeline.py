from model.inference import predict
from rag.retriever import retrieve_treatment
from forecast.weather import get_forecast, get_location_name
from forecast.risk_model import predict_spread_risk
from utils.response_generator import (
    generate_disease_response,
    generate_healthy_response,
)
from PIL import Image
import io

def run_pipeline(
    image_bytes: bytes,
    lat: float,
    lon: float,
    lang: str = "telugu"
) -> dict:
    """
    Full CropSense pipeline:
    image + location → disease + treatment + weather risk + LLM response
    """
    # Step 1 — Disease detection
    image      = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    predictions = predict(image, top_k=3)
    top         = predictions[0]
    disease_key = top["disease"]
    confidence  = top["confidence"]
    is_healthy  = "healthy" in disease_key.lower()

    # Step 2 — Weather forecast + spread risk
    forecast    = get_forecast(lat, lon)
    weather_risk = predict_spread_risk(disease_key, forecast)
    location_name = get_location_name(lat, lon)

    # Step 3 — LLM response
    if is_healthy:
        crop_name = disease_key.split("___")[0].replace("_", " ")
        response  = generate_healthy_response(crop_name, confidence, lang)
    else:
        response = generate_disease_response(
            disease_key, confidence, weather_risk, lang
        )

    return {
        "disease_key":    disease_key,
        "confidence":     confidence,
        "is_healthy":     is_healthy,
        "top_predictions": predictions,
        "weather_risk":   weather_risk,
        "location_name":  location_name,
        "response":       response,
        "lang":           lang,
    }