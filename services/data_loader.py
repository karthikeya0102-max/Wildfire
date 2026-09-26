"""Load local wildfire evidence datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _safe_load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return df


def load_fire_data() -> pd.DataFrame:
    df = _safe_load_csv(DATA_DIR / "fires_sample.csv")
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "latitude", "longitude", "timestamp", "confidence", "frp", "source", "satellite"
        ])

    expected = ["id", "latitude", "longitude", "timestamp", "confidence", "frp", "source", "satellite"]
    for column in expected:
        if column not in df.columns:
            df[column] = pd.NA

    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.5)
    df["confidence"] = df["confidence"].clip(0, 1)
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df


def load_weather_data() -> pd.DataFrame:
    df = _safe_load_csv(DATA_DIR / "weather_sample.csv")
    if df.empty:
        return pd.DataFrame(columns=[
            "latitude", "longitude", "timestamp", "temperature_c", "humidity_pct", "wind_speed_kmh",
            "wind_direction_deg", "precipitation_mm", "source"
        ])

    required = [
        "latitude", "longitude", "timestamp", "temperature_c", "humidity_pct",
        "wind_speed_kmh", "wind_direction_deg", "precipitation_mm", "source"
    ]
    for column in required:
        if column not in df.columns:
            df[column] = pd.NA

    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce").fillna(30.0)
    df["humidity_pct"] = pd.to_numeric(df["humidity_pct"], errors="coerce").fillna(35.0)
    df["wind_speed_kmh"] = pd.to_numeric(df["wind_speed_kmh"], errors="coerce").fillna(15.0)
    df["wind_direction_deg"] = pd.to_numeric(df["wind_direction_deg"], errors="coerce").fillna(180.0)
    df["precipitation_mm"] = pd.to_numeric(df["precipitation_mm"], errors="coerce").fillna(0.0)
    return df


def load_incident_data() -> pd.DataFrame:
    df = _safe_load_csv(DATA_DIR / "incidents_sample.csv")
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "latitude", "longitude", "timestamp", "text", "source", "confidence"
        ])

    required = ["id", "latitude", "longitude", "timestamp", "text", "source", "confidence"]
    for column in required:
        if column not in df.columns:
            df[column] = pd.NA

    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.5)
    df["confidence"] = df["confidence"].clip(0, 1)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df


def load_all_evidence() -> dict[str, pd.DataFrame]:
    return {
        "fires": load_fire_data(),
        "weather": load_weather_data(),
        "incidents": load_incident_data(),
    }
