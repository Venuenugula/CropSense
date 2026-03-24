"""
ML-based spread-risk classifier (XGBoost) trained on Meteostat history.

Inference uses the same engineered features built from the live OpenWeather
7-day forecast (see `build_ml_features_from_forecast`).

If ``forecast/risk_model.pkl`` is missing, callers should fall back to rules
(see ``risk_model.py``).
"""
from __future__ import annotations

import os

import joblib
import numpy as np

ROOT = os.path.dirname(__file__)
MODEL_PATH = os.path.join(ROOT, "risk_model.pkl")

FEATURE_ORDER = [
    "temp",
    "humidity",
    "rain",
    "temp_avg_3",
    "humidity_avg_3",
    "rain_sum_7",
    "temp_trend",
    "humidity_trend",
]

_CLASS_TO_LEVEL = {0: "Low", 1: "Medium", 2: "High"}
_SCORE_WEIGHTS = np.array([0.22, 0.52, 0.88], dtype=np.float64)


_model = None


def _load_model():
    global _model
    if _model is None:
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(f"ML risk model not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
    return _model


def ml_model_available() -> bool:
    return os.path.isfile(MODEL_PATH)


def build_ml_features_from_forecast(forecast: list[dict]) -> dict[str, float]:
    """
    Map OpenWeather daily dicts (``avg_temp``, ``avg_humidity``, ``total_rain``)
    to the feature vector used at training time.
    """
    if not forecast:
        raise ValueError("forecast is empty")

    days = forecast[:7]
    temps = [float(d["avg_temp"]) for d in days]
    hums = [float(d["avg_humidity"]) for d in days]
    rains = [float(d["total_rain"]) for d in days]

    temp = temps[-1]
    humidity = hums[-1]
    rain = rains[-1]
    temp_avg_3 = float(np.mean(temps[-3:])) if len(temps) >= 3 else float(np.mean(temps))
    humidity_avg_3 = float(np.mean(hums[-3:])) if len(hums) >= 3 else float(np.mean(hums))
    rain_sum_7 = float(np.sum(rains))
    temp_trend = float(temps[-1] - temps[-2]) if len(temps) >= 2 else 0.0
    humidity_trend = float(hums[-1] - hums[-2]) if len(hums) >= 2 else 0.0

    return {
        "temp": temp,
        "humidity": humidity,
        "rain": rain,
        "temp_avg_3": temp_avg_3,
        "humidity_avg_3": humidity_avg_3,
        "rain_sum_7": rain_sum_7,
        "temp_trend": temp_trend,
        "humidity_trend": humidity_trend,
    }


def predict_risk_level_and_score(forecast: list[dict]) -> tuple[str, float, np.ndarray]:
    """
    Returns (risk_level, risk_score, proba_vector).

    ``risk_score`` blends class probabilities with weights ~ Low/Medium/High
    so it stays comparable to the 0–1 rule-based score in ``risk_model.py``.
    """
    model = _load_model()
    feats = build_ml_features_from_forecast(forecast)
    row = np.array([[feats[k] for k in FEATURE_ORDER]], dtype=np.float64)
    proba = model.predict_proba(row)[0]
    classes = model.classes_
    pred_idx = int(np.argmax(proba))
    pred_label = int(classes[pred_idx])
    risk_level = _CLASS_TO_LEVEL.get(pred_label, "Medium")
    weights = np.array(
        [_SCORE_WEIGHTS[int(c)] if int(c) in (0, 1, 2) else 0.5 for c in classes],
        dtype=np.float64,
    )
    risk_score = float(np.dot(proba, weights))
    return risk_level, risk_score, proba
