"""Deterministic situation-summary generation."""

from __future__ import annotations

from typing import Any


def summarize_zone(zone: dict[str, Any]) -> str:
    detections = zone.get("detections", [])
    weather_records = zone.get("weather_records", [])
    incidents = zone.get("incident_records", [])

    if not detections:
        return "No fire detections were available for this zone."

    high_confidence = sum(1 for item in detections if float(item.get("confidence", 0)) >= 0.75)
    avg_frp = sum(float(item.get("frp", 0.0)) for item in detections) / max(len(detections), 1)
    weather = weather_records[0] if weather_records else {}
    temp = weather.get("temperature_c", "unknown")
    humidity = weather.get("humidity_pct", "unknown")
    wind = weather.get("wind_speed_kmh", "unknown")
    incident_text = incidents[0].get("text", "a simulated incident report") if incidents else "no simulated incident report"

    summary = (
        f"Zone {zone.get('zone_id')} contains {len(detections)} fire detections "
        f"with {high_confidence} high-confidence satellite detections and elevated FRP. "
        f"The associated weather record indicates {temp}°C temperature, {humidity}% relative humidity and {wind} km/h wind speed. "
        f"A simulated incident report also describes '{incident_text}'. "
        "The system therefore prioritizes this zone for human review."
    )
    return summary
