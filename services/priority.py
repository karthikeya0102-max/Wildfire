"""Deterministic scoring utilities for review priority and confidence."""

from __future__ import annotations


def clamp(value: float | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(maximum, float(value)))


def _safe_value(value: float | None) -> float:
    return 0.0 if value is None else clamp(float(value), 0.0, 1.0)


def calculate_priority(fire: float | None, weather: float | None, incident: float | None, temporal: float | None) -> float:
    """Compute a transparent prototype review priority on a 0-1 scale.

    The weightings are intentionally simple and explainable:
    - fire detection evidence: 35%
    - weather conditions: 25%
    - incident evidence: 20%
    - temporal/spatial consistency: 20%
    """
    fire_score = _safe_value(fire)
    weather_score = _safe_value(weather)
    incident_score = _safe_value(incident)
    temporal_score = _safe_value(temporal)

    score = (
        0.35 * fire_score
        + 0.25 * weather_score
        + 0.20 * incident_score
        + 0.20 * temporal_score
    )
    return clamp(score)


def calculate_confidence(
    fire_confidence: float | None,
    incident_confidence: float | None,
    weather_score: float | None,
    evidence_count: int = 1,
) -> float:
    """Prototype confidence heuristic based on agreement and coverage."""
    evidence = [
        _safe_value(fire_confidence),
        _safe_value(incident_confidence),
        _safe_value(weather_score),
    ]
    average_agreement = sum(evidence) / len(evidence) if evidence else 0.0
    coverage = min(1.0, evidence_count / 4.0)
    confidence = 0.65 * average_agreement + 0.35 * coverage
    return clamp(confidence)


def priority_label(score: float | None) -> str:
    score_value = clamp(score)
    if score_value >= 0.7:
        return "HIGH"
    if score_value >= 0.4:
        return "MEDIUM"
    return "LOW"
