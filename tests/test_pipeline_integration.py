import io
import importlib
import sys
import types

from PIL import Image


def _sample_image_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(180, 220, 120))
    # Add simple texture so quality-check variance isn't too low.
    for x in range(0, 64, 4):
        for y in range(0, 64, 4):
            img.putpixel((x, y), (30, 120, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_run_pipeline_logs_detection(monkeypatch):
    fake_inference = types.ModuleType("model.inference")
    fake_inference.predict = lambda image, top_k=3: [
        {"disease": "Tomato___Late_blight", "confidence": 91.0},
        {"disease": "Tomato___Early_blight", "confidence": 6.0},
        {"disease": "Tomato___healthy", "confidence": 3.0},
    ]
    monkeypatch.setitem(sys.modules, "model.inference", fake_inference)

    fake_retriever = types.ModuleType("rag.retriever")
    fake_retriever.retrieve_treatment = lambda disease_key, query=None: {}
    monkeypatch.setitem(sys.modules, "rag.retriever", fake_retriever)

    pipeline = importlib.import_module("bot.pipeline")

    monkeypatch.setattr(
        pipeline,
        "get_forecast",
        lambda lat, lon: [
            {
                "date": "2026-03-20",
                "avg_temp": 24.0,
                "avg_humidity": 88.0,
                "total_rain": 10.0,
                "description": "rain",
            }
        ]
        * 7,
    )
    monkeypatch.setattr(pipeline, "get_location_name", lambda lat, lon: "Basar, Telangana")
    monkeypatch.setattr(
        pipeline,
        "predict_spread_risk",
        lambda disease_key, forecast: {"risk_level": "High", "risk_score": 0.81},
    )
    monkeypatch.setattr(
        pipeline,
        "generate_disease_response",
        lambda disease_key, confidence, weather_risk, lang, top_predictions=None: "mock response",
    )

    captured = {}

    def _log_detection(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(pipeline, "log_detection", _log_detection)

    result = pipeline.run_pipeline(
        image_bytes=_sample_image_bytes(),
        lat=18.95,
        lon=79.13,
        lang="english",
        user_id=12345,
    )

    assert result["disease_key"] == "Tomato___Late_blight"
    assert result["weather_risk"]["risk_level"] == "High"
    assert captured["user_id"] == 12345
    assert captured["disease_key"] == "Tomato___Late_blight"
    assert captured["location_name"] == "Basar, Telangana"
    assert captured["risk_level"] == "High"


def test_run_pipeline_marks_uncertain_for_low_confidence(monkeypatch):
    pipeline = importlib.import_module("bot.pipeline")
    monkeypatch.setattr(
        pipeline,
        "predict",
        lambda image, top_k=3: [
            {"disease": "Tomato___Late_blight", "confidence": 42.0},
            {"disease": "Tomato___Early_blight", "confidence": 40.0},
            {"disease": "Tomato___healthy", "confidence": 18.0},
        ],
    )
    monkeypatch.setattr(pipeline, "get_forecast", lambda lat, lon: [{"date": "d", "avg_temp": 24, "avg_humidity": 88, "total_rain": 10, "description": "rain"}] * 7)
    monkeypatch.setattr(pipeline, "get_location_name", lambda lat, lon: "Basar, Telangana")
    monkeypatch.setattr(pipeline, "predict_spread_risk", lambda disease_key, forecast: {"risk_level": "Medium", "risk_score": 0.5})
    monkeypatch.setattr(pipeline, "log_detection", lambda **kwargs: None)

    result = pipeline.run_pipeline(
        image_bytes=_sample_image_bytes(),
        lat=18.95,
        lon=79.13,
        lang="english",
        user_id=1,
    )
    assert result["uncertain"] is True
    assert "low" in result["response"].lower()
