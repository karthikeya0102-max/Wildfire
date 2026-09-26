"""Weather access layer with local fallback behaviour."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from services.data_loader import load_weather_data

BASE_DIR = Path(__file__).resolve().parent.parent


def local_weather_sample() -> pd.DataFrame:
    return load_weather_data()


def fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    """Attempt Open-Meteo weather retrieval, falling back to bundled sample data."""
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
        "timezone": "auto",
    }
    try:
        response = requests.get(api_url, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current", {})
        if not current:
            raise ValueError("No weather data returned")
        return {
            "latitude": lat,
            "longitude": lon,
            "timestamp": current.get("time", "unknown"),
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_direction_deg": current.get("wind_direction_10m"),
            "precipitation_mm": current.get("precipitation", 0),
            "source": "OPEN_METEO",
        }
    except Exception:
        sample = local_weather_sample()
        if sample.empty:
            return {
                "latitude": lat,
                "longitude": lon,
                "timestamp": "unknown",
                "temperature_c": 30.0,
                "humidity_pct": 35.0,
                "wind_speed_kmh": 14.0,
                "wind_direction_deg": 180.0,
                "precipitation_mm": 0.0,
                "source": "SAMPLE_FALLBACK",
            }

        nearest = sample.iloc[(sample[["latitude", "longitude"]].sub([lat, lon]).pow(2).sum(axis=1).idxmin())]
        return {
            "latitude": lat,
            "longitude": lon,
            "timestamp": nearest.get("timestamp", "unknown"),
            "temperature_c": float(nearest.get("temperature_c", 30.0)),
            "humidity_pct": float(nearest.get("humidity_pct", 35.0)),
            "wind_speed_kmh": float(nearest.get("wind_speed_kmh", 15.0)),
            "wind_direction_deg": float(nearest.get("wind_direction_deg", 180.0)),
            "precipitation_mm": float(nearest.get("precipitation_mm", 0.0)),
            "source": "SAMPLE_FALLBACK",
        }
