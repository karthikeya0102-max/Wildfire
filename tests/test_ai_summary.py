import os

from services.llm import generate_ai_summary


def test_generate_ai_summary_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    zone = {
        "zone_id": "Z001",
        "detections": [{"id": "F001", "confidence": 0.9, "frp": 100.0}],
        "weather_records": [{"temperature_c": 41.2, "humidity_pct": 18, "wind_speed_kmh": 31.4}],
        "incident_records": [{"text": "Smoke reported near the eastern road."}],
    }
    summary = generate_ai_summary(zone)
    assert "Zone Z001" in summary
    assert "human review" in summary.lower()


def test_generate_ai_summary_uses_template_when_api_unavailable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    zone = {
        "zone_id": "Z002",
        "detections": [{"id": "F002", "confidence": 0.8, "frp": 80.0}],
        "weather_records": [{"temperature_c": 39.0, "humidity_pct": 25, "wind_speed_kmh": 27.0}],
        "incident_records": [],
    }
    summary = generate_ai_summary(zone)
    assert isinstance(summary, str)
    assert len(summary) > 20
