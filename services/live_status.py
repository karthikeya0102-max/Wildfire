"""Helpers for live-data status reporting."""

from __future__ import annotations

import os


def get_live_status() -> dict[str, str]:
    """Return the current status of optional live data integrations."""
    return {
        "firms": "configured" if os.getenv("FIRMS_MAP_KEY") else "fallback",
        "weather": "live" if os.getenv("OPEN_METEO_ENABLED", "true").lower() == "true" else "fallback",
        "nemotron": "configured" if os.getenv("NEMOTRON_API_KEY") else "fallback",
    }
