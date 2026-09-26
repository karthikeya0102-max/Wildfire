# Wildfire Intelligence & Human Review

A local, prototype wildfire decision-support dashboard built with Streamlit. The app combines satellite fire detections, weather, and simulated incident reports into a review-priority score for human review.

## Purpose

This system does not make autonomous life-critical decisions, issue evacuation orders, or claim deterministic fire-behavior prediction. It is a multimodal decision-support prototype for prioritizing human review.

## Priority Score

The review priority is a transparent deterministic score on a 0-1 scale using weighted evidence components.

Formula:

priority = 0.35 * fire_score + 0.25 * weather_score + 0.20 * incident_score + 0.20 * temporal_score

Where each component is normalized to 0-1. The output is labeled as HIGH, MEDIUM, or LOW for human review prioritization and is not a calibrated probability or emergency decision metric.

## Confidence and Uncertainty

Confidence is a prototype heuristic based on the average evidence agreement and coverage. Uncertainty is defined as 1 - confidence.

This is a prototype uncertainty heuristic and is not a calibrated probability.

## Running locally

1. Create a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Start the app:
   streamlit run app.py

## Data behavior

- NASA FIRMS is used when credentials are available, but the app falls back to local bundled sample data when unavailable.
- Weather attempts Open-Meteo first and falls back to local data.
- Simulated incident reports are clearly marked as SIMULATED and are never presented as real-world observations.

## Evaluation status

Ground-truth labels were not available for this simulated prototype; quantitative detection performance could not be independently validated.

## Safety

This system provides decision support for human review. It does not make autonomous life-critical decisions.
