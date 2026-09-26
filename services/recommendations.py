"""Prototype resource-planning suggestions derived from zone evidence."""

from __future__ import annotations

import math
from typing import Any


def _estimated_footprint_km2(detections: list[dict[str, Any]]) -> float | None:
    coordinates = set()
    for detection in detections:
        try:
            latitude = float(detection["latitude"])
            longitude = float(detection["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            coordinates.add((latitude, longitude))

    if len(coordinates) < 2:
        return None

    latitudes = [point[0] for point in coordinates]
    longitudes = [point[1] for point in coordinates]
    mean_latitude = sum(latitudes) / len(latitudes)
    height_km = max((max(latitudes) - min(latitudes)) * 111.32, 1.0)
    width_km = max(
        (max(longitudes) - min(longitudes)) * 111.32 * abs(math.cos(math.radians(mean_latitude))),
        1.0,
    )
    return height_km * width_km


def build_resource_recommendations(zone: dict[str, Any]) -> dict[str, Any]:
    """Return transparent, non-operational planning estimates for a fire zone."""
    detections = zone.get("detections", [])
    fire_count = len(detections)
    priority = float(zone.get("priority", 0.0) or 0.0)

    if not fire_count:
        personnel_range = "Not estimated"
    elif priority >= 0.7 or fire_count >= 5:
        personnel_range = "8-12 (illustrative)"
    elif priority >= 0.4 or fire_count >= 3:
        personnel_range = "4-8 (illustrative)"
    else:
        personnel_range = "2-4 (illustrative)"

    footprint_km2 = _estimated_footprint_km2(detections)
    density_per_100_km2 = (
        fire_count / footprint_km2 * 100.0
        if footprint_km2 is not None and footprint_km2 > 0
        else None
    )

    equipment = [
        "Wildland PPE and communications radios",
        "Hand tools; confirm water and engine access",
    ]
    if detections:
        average_frp = sum(float(detection.get("frp", 0.0) or 0.0) for detection in detections) / fire_count
        if average_frp >= 100:
            equipment.append("Assess engine and water support after field size-up")

    weather_records = zone.get("weather_records", [])
    wind_speeds = [
        float(record["wind_speed_kmh"])
        for record in weather_records
        if record.get("wind_speed_kmh") is not None
    ]
    if wind_speeds and sum(wind_speeds) / len(wind_speeds) >= 25:
        equipment.append("Monitor wind shifts and potential spot fires")

    if zone.get("incident_records"):
        equipment.append("Verify reported conditions with local incident command")

    return {
        "personnel_range": personnel_range,
        "estimated_footprint_km2": footprint_km2,
        "detection_density_per_100_km2": density_per_100_km2,
        "equipment": equipment,
    }