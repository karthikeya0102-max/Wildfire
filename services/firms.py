"""Optional FIRMS access layer with bundled local fallback."""

from __future__ import annotations

import csv
import io
import os
from typing import Any

import pandas as pd
import requests

from services.data_loader import load_fire_data


def local_fire_sample() -> pd.DataFrame:
    return load_fire_data()


def fetch_firms_detections(lat: float, lon: float, radius_km: int = 100) -> list[dict[str, Any]]:
    """Try NASA FIRMS when an API key is present; otherwise return local dataset."""
    api_key = os.getenv("FIRMS_MAP_KEY")
    if api_key:
        try:
            min_lat = max(-90.0, lat - 1.5)
            max_lat = min(90.0, lat + 1.5)
            min_lon = max(-180.0, lon - 1.5)
            max_lon = min(180.0, lon + 1.5)
            url = (
                "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/"
                "{min_lat},{max_lat},{min_lon},{max_lon}"
            ).format(
                key=api_key,
                min_lat=min_lat,
                max_lat=max_lat,
                min_lon=min_lon,
                max_lon=max_lon,
            )
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            text = response.text.strip()
            if text:
                reader = csv.DictReader(io.StringIO(text))
                rows = list(reader)
                if rows:
                    normalized = []
                    for row in rows[:20]:
                        try:
                            normalized.append({
                                "id": row.get("id") or row.get("latitude"),
                                "latitude": float(row.get("latitude", lat)),
                                "longitude": float(row.get("longitude", lon)),
                                "timestamp": row.get("acq_date") or row.get("acquisition_date") or row.get("timestamp") or "unknown",
                                "confidence": float(row.get("confidence", 0.5)) / 100.0 if row.get("confidence") else 0.5,
                                "frp": float(row.get("frp", 0.0) or 0.0),
                                "source": "NASA_FIRMS",
                                "satellite": row.get("instrument", row.get("satellite", "VIIRS")),
                            })
                        except Exception:
                            continue
                    if normalized:
                        return normalized
        except Exception:
            pass

    sample = local_fire_sample()
    if sample.empty:
        return []
    nearby = sample[
        (sample["latitude"].sub(lat).abs() <= 0.35)
        & (sample["longitude"].sub(lon).abs() <= 0.35)
    ]
    if nearby.empty:
        nearby = sample.head(5)
    return nearby.to_dict("records")
