import os

# Deterministic tests: hybrid ML (if ``risk_model.pkl`` exists) can disagree with rules.
os.environ["USE_ML_SPREAD_RISK"] = "0"

from forecast.risk_model import predict_spread_risk


def _make_forecast(temp: float, humidity: float, rain: float) -> list[dict]:
    return [
        {
            "date": f"2026-03-{10 + i}",
            "avg_temp": temp,
            "avg_humidity": humidity,
            "total_rain": rain,
            "description": "rain",
        }
        for i in range(7)
    ]


def test_predict_spread_risk_returns_low_for_healthy():
    forecast = _make_forecast(temp=28, humidity=85, rain=12)
    result = predict_spread_risk("Tomato___healthy", forecast)
    assert result["risk_level"] == "Low"
    assert result["risk_score"] == 0.0
    assert result["daily"] == []


def test_predict_spread_risk_high_for_fungal_favorable_weather():
    forecast = _make_forecast(temp=24, humidity=92, rain=15)
    result = predict_spread_risk("Tomato___Late_blight", forecast)
    assert result["risk_level"] in {"Medium", "High"}
    assert result["risk_score"] >= 0.35
    assert len(result["daily"]) == 7
