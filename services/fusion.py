"""Zone construction and multimodal fusion for wildfire review prioritization."""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.data_loader import load_fire_data, load_incident_data, load_weather_data
from services.priority import calculate_confidence, calculate_priority, clamp, priority_label


def _normalize_fire_signal(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    avg_conf = df["confidence"].mean() if "confidence" in df.columns else 0.0
    avg_frp = df["frp"].mean() if "frp" in df.columns else 0.0
    fire_signal = 0.7 * clamp(avg_conf) + 0.3 * clamp(avg_frp / 200.0)
    return float(fire_signal)


def _normalize_weather_signal(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    temp = pd.to_numeric(df["temperature_c"], errors="coerce").fillna(30.0).mean()
    humidity = pd.to_numeric(df["humidity_pct"], errors="coerce").fillna(40.0).mean()
    wind = pd.to_numeric(df["wind_speed_kmh"], errors="coerce").fillna(12.0).mean()
    precip = pd.to_numeric(df["precipitation_mm"], errors="coerce").fillna(0.0).mean()
    temp_signal = clamp((temp - 20) / 30, 0.0, 1.0)
    humidity_signal = clamp((40 - humidity) / 40, 0.0, 1.0)
    wind_signal = clamp(wind / 50.0, 0.0, 1.0)
    precip_signal = clamp(1.0 - precip / 5.0, 0.0, 1.0)
    weather_signal = 0.4 * temp_signal + 0.3 * humidity_signal + 0.2 * wind_signal + 0.1 * precip_signal
    return float(clamp(weather_signal))


def _normalize_incident_signal(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    avg_conf = df["confidence"].mean() if "confidence" in df.columns else 0.0
    incident_signal = clamp(avg_conf)
    return float(incident_signal)


def _temporal_signal(zone_detections: pd.DataFrame) -> float:
    if zone_detections.empty:
        return 0.0
    timestamps = pd.to_datetime(zone_detections["timestamp"], errors="coerce")
    timestamps = timestamps.dropna()
    if timestamps.empty:
        return 0.5
    span_hours = (timestamps.max() - timestamps.min()).total_seconds() / 3600.0
    signal = clamp(1.0 - (span_hours / 24.0), 0.0, 1.0)
    return float(signal)


def build_zones() -> list[dict[str, Any]]:
    fires = load_fire_data()
    incidents = load_incident_data()
    weather = load_weather_data()

    if fires.empty:
        return []

    approx_lat = 0.15
    approx_lon = 0.20
    zones: list[dict[str, Any]] = []
    for _, fire in fires.iterrows():
        centroid_lat = round(float(fire["latitude"]), 3)
        centroid_lon = round(float(fire["longitude"]), 3)
        match = [
            z
            for z in zones
            if abs(z["center_latitude"] - centroid_lat) <= approx_lat
            and abs(z["center_longitude"] - centroid_lon) <= approx_lon
        ]
        if match:
            zone = match[0]
            zone["detections"].append(fire.to_dict())
            zone["fire_count"] += 1
        else:
            zones.append({
                "zone_id": f"Z{len(zones) + 1:03d}",
                "center_latitude": centroid_lat,
                "center_longitude": centroid_lon,
                "detections": [fire.to_dict()],
                "fire_count": 1,
                "weather_records": [],
                "incident_records": [],
            })

    for zone in zones:
        dets = pd.DataFrame(zone["detections"])
        zone_lat = zone["center_latitude"]
        zone_lon = zone["center_longitude"]

        nearby_weather = weather[
            (weather["latitude"].sub(zone_lat).abs() <= 0.25)
            & (weather["longitude"].sub(zone_lon).abs() <= 0.25)
        ]
        nearby_incidents = incidents[
            (incidents["latitude"].sub(zone_lat).abs() <= 0.25)
            & (incidents["longitude"].sub(zone_lon).abs() <= 0.25)
        ]
        zone["weather_records"] = nearby_weather.to_dict("records")
        zone["incident_records"] = nearby_incidents.to_dict("records")

        fire_signal = _normalize_fire_signal(dets)
        weather_signal = _normalize_weather_signal(nearby_weather)
        incident_signal = _normalize_incident_signal(nearby_incidents)
        temporal_score = _temporal_signal(dets)

        priority = calculate_priority(fire_signal, weather_signal, incident_signal, temporal_score)
        confidence = calculate_confidence(
            fire_confidence=float(dets["confidence"].mean()) if not dets.empty else None,
            incident_confidence=float(nearby_incidents["confidence"].mean()) if not nearby_incidents.empty else None,
            weather_score=clamp(weather_signal),
            evidence_count=max(len(dets), len(nearby_incidents), 1),
        )
        uncertainty = 1.0 - confidence
        zone["priority"] = priority
        zone["confidence"] = confidence
        zone["uncertainty"] = uncertainty
        zone["label"] = priority_label(priority)
        zone["evidence_factors"] = {
            "fire_signal": fire_signal,
            "weather_signal": weather_signal,
            "incident_signal": incident_signal,
            "temporal_signal": temporal_score,
        }

    return zones


def build_review_queue() -> list[dict[str, Any]]:
    zones = build_zones()
    return sorted(zones, key=lambda z: z["priority"], reverse=True)
