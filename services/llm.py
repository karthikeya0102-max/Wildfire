"""Optional AI summary service with deterministic fallback."""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _structured_payload(zone: dict[str, Any]) -> dict[str, Any]:
    detections = zone.get("detections", [])
    weather = zone.get("weather_records", [])
    incidents = zone.get("incident_records", [])

    return {
        "zone_id": zone.get("zone_id"),
        "detection_count": len(detections),
        "high_confidence_detections": sum(1 for det in detections if float(det.get("confidence", 0)) >= 0.75),
        "avg_frp": sum(float(det.get("frp", 0.0)) for det in detections) / max(len(detections), 1),
        "weather": weather[0] if weather else {},
        "incident_texts": [item.get("text", "") for item in incidents],
        "priority": zone.get("priority"),
        "confidence": zone.get("confidence"),
        "uncertainty": zone.get("uncertainty"),
        "source_note": "This summary is generated from structured evidence only and may include uncertainty.",
    }


def _get_llm_config() -> tuple[str, str, str, str]:
    provider = os.getenv("LLM_PROVIDER", "nemotron").lower()
    api_key = os.getenv("NEMOTRON_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    base_url = os.getenv("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    model = os.getenv("NEMOTRON_MODEL", "nemotron-3.5-lightning-30b-a3b")
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", api_key)
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return provider, api_key, base_url, model


def generate_template_summary(zone: dict[str, Any]) -> str:
    detections = zone.get("detections", [])
    weather = zone.get("weather_records", [])
    incidents = zone.get("incident_records", [])

    if not detections:
        return "No fire detections were available for this zone."

    high_confidence = sum(1 for det in detections if float(det.get("confidence", 0)) >= 0.75)
    avg_frp = sum(float(det.get("frp", 0.0)) for det in detections) / max(len(detections), 1)
    weather_record = weather[0] if weather else {}
    weather_text = (
        f"The associated weather record indicates {weather_record.get('temperature_c', 'unknown')}°C temperature, "
        f"{weather_record.get('humidity_pct', 'unknown')}% relative humidity and {weather_record.get('wind_speed_kmh', 'unknown')} km/h wind speed."
    )
    incident_text = incidents[0].get("text", "No simulated incident report was recorded.") if incidents else "No simulated incident report was recorded."
    return (
        f"Zone {zone.get('zone_id')} contains {len(detections)} fire detections with {high_confidence} high-confidence satellite detections and elevated FRP ({avg_frp:.1f}). "
        f"{weather_text} A simulated incident report also describes '{incident_text}'. The system therefore prioritizes this zone for human review."
    )


def generate_ai_summary(zone: dict[str, Any]) -> str:
    """Optional LLM summary. If the configured provider is unavailable, fall back to the deterministic template."""
    provider, api_key, base_url, model = _get_llm_config()
    if not api_key:
        return generate_template_summary(zone)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You summarize wildfire evidence for a human-review dashboard. "
                    "Use only the provided structured evidence. Describe uncertainty and never invent facts. "
                    "Do not claim certainty or generate evacuation orders."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(_structured_payload(zone)),
            },
        ],
        "temperature": 0.2,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if provider == "nemotron":
        url = f"{base_url}/chat/completions"
    elif provider == "openai":
        url = f"{base_url}/chat/completions"
    else:
        return generate_template_summary(zone)

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        response.raise_for_status()
        data = response.json()
        msg = data["choices"][0]["message"]["content"]
        if msg:
            return msg.strip()
    except Exception:
        return generate_template_summary(zone)

    return generate_template_summary(zone)
