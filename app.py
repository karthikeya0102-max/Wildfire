from __future__ import annotations

import os
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import folium_static

load_dotenv()

from services.data_loader import load_fire_data, load_incident_data, load_weather_data
from services.firms import fetch_firms_detections
from services.fusion import build_review_queue
from services.live_status import get_live_status
from services.llm import generate_ai_summary
from services.recommendations import build_resource_recommendations
from services.summary import summarize_zone
from services.weather import fetch_weather

st.set_page_config(page_title="Wildfire Intelligence & Human Review", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
        color: #e5e7eb;
    }
    div[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(148, 163, 184, 0.2);
    }
    .stMetric {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 0.7rem 0.8rem;
    }
    .stAlert {
        border-radius: 12px;
    }
    .block-container {
        padding-top: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Wildfire Intelligence & Human Review")
st.caption("Multimodal decision-support prototype")

st.warning("This system provides decision support for human review. It does not make autonomous life-critical decisions.")

if "selected_zone" not in st.session_state:
    st.session_state.selected_zone = ""

if "priority_filter" not in st.session_state:
    st.session_state.priority_filter = "ALL"


def refresh_evidence(use_live: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]]:
    fires = load_fire_data()
    weather = load_weather_data()
    incidents = load_incident_data()

    if use_live:
        center_lat = float(fires["latitude"].mean()) if not fires.empty else 0.0
        center_lon = float(fires["longitude"].mean()) if not fires.empty else 0.0
        live_fires = fetch_firms_detections(center_lat, center_lon, radius_km=200)
        if live_fires:
            fires = pd.DataFrame(live_fires)

        live_weather = fetch_weather(center_lat, center_lon)
        weather = pd.DataFrame([live_weather])

    queue = build_review_queue()
    return fires, weather, incidents, queue


fires, weather, incidents, queue = refresh_evidence()

with st.sidebar:
    st.header("Operational status")
    status = get_live_status()
    st.markdown("### Data sources")
    st.write(f"- Fire detections: {status['firms']}")
    st.write(f"- Weather: {status['weather']}")
    st.write(f"- AI summary: {status['nemotron']}")
    st.write("- Incidents: local SIMULATED incident reports in [data/incidents_sample.csv](data/incidents_sample.csv)")
    st.write("- Live API access: optional if FIRMS_MAP_KEY is set and the remote service responds.")

    st.divider()
    st.subheader("Controls")
    refresh_clicked = st.button("Refresh evidence", use_container_width=True)
    if refresh_clicked:
        fires, weather, incidents, queue = refresh_evidence(use_live=bool(os.getenv("FIRMS_MAP_KEY")))
        st.session_state.selected_zone = queue[0]["zone_id"] if queue else ""
        st.rerun()

    use_live = st.checkbox("Try live API source when available", value=bool(os.getenv("FIRMS_MAP_KEY")))
    if use_live:
        st.info("Live requests are optional and will fall back safely to local sample data if unavailable.")
        fires, weather, incidents, queue = refresh_evidence(use_live=True)

    provider = os.getenv("LLM_PROVIDER", "nemotron").upper()
    ai_key = os.getenv("NEMOTRON_API_KEY") or os.getenv("OPENAI_API_KEY")
    if ai_key:
        st.success(f"AI summary mode is enabled for {provider}.")
    else:
        st.caption("No configured LLM API key was found; the app will use the deterministic template summary instead.")

    st.subheader("Priority filters")
    filter_cols = st.columns(4)
    if filter_cols[0].button("ALL", use_container_width=True):
        st.session_state.priority_filter = "ALL"
    if filter_cols[1].button("HIGH", use_container_width=True):
        st.session_state.priority_filter = "HIGH"
    if filter_cols[2].button("MEDIUM", use_container_width=True):
        st.session_state.priority_filter = "MEDIUM"
    if filter_cols[3].button("LOW", use_container_width=True):
        st.session_state.priority_filter = "LOW"

    st.divider()
    export_summary = st.button("Export selected summary", use_container_width=True)
    if export_summary and queue:
        selected_zone = next((z for z in queue if z["zone_id"] == st.session_state.selected_zone), queue[0])
        summary_path = Path("exports") / "selected_zone_summary.txt"
        summary_path.parent.mkdir(exist_ok=True)
        summary_path.write_text(summarize_zone(selected_zone), encoding="utf-8")
        st.success(f"Summary exported to {summary_path}")

# KPI cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Fire Detections", len(fires))
col2.metric("High Priority Zones", sum(1 for zone in queue if zone["priority"] >= 0.7))
col3.metric("Average Fire Confidence", round(float(fires["confidence"].mean()), 2) if not fires.empty else 0.0)
col4.metric("Average Temperature", round(float(weather["temperature_c"].mean()), 1) if not weather.empty else 0.0)

if queue and not st.session_state.selected_zone:
    st.session_state.selected_zone = queue[0]["zone_id"]

priority_filter = st.session_state.priority_filter
filtered_queue = queue
if priority_filter != "ALL":
    filtered_queue = [zone for zone in queue if zone["label"] == priority_filter]
if not filtered_queue:
    filtered_queue = queue

left_col, right_col = st.columns([2, 1])

with left_col:
    if filtered_queue:
        zone_ids = [zone["zone_id"] for zone in filtered_queue]
        if st.session_state.selected_zone not in zone_ids:
            st.session_state.selected_zone = zone_ids[0]
        selected = st.selectbox("Select zone", zone_ids, index=zone_ids.index(st.session_state.selected_zone))
        st.session_state.selected_zone = selected
        zone = next(z for z in filtered_queue if z["zone_id"] == selected)
        center = [zone["center_latitude"], zone["center_longitude"]]
        m = folium.Map(location=center, zoom_start=9, tiles="OpenStreetMap")
        for det in zone["detections"]:
            folium.CircleMarker(
                location=[float(det["latitude"]), float(det["longitude"])],
                radius=8,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.6,
                popup=f"{det['id']}\nPriority {zone['priority']:.2f}",
            ).add_to(m)
        for other in filtered_queue:
            folium.Marker(
                location=[float(other["center_latitude"]), float(other["center_longitude"])],
                popup=f"{other['zone_id']} | priority {other['priority']:.2f}",
                icon=folium.Icon(color="orange" if other["priority"] >= 0.7 else "blue" if other["priority"] >= 0.4 else "green"),
            ).add_to(m)
        st.caption("Map legend: orange = HIGH, blue = MEDIUM, green = LOW")
        folium_static(m, width=700, height=500)
    else:
        st.info("No fire zones were available from the local data source.")

with right_col:
    st.subheader("Prioritized Review Queue")
    for zone in filtered_queue:
        zone_button_key = f"zone_{zone['zone_id']}"
        if st.button(f"Focus {zone['zone_id']}", key=zone_button_key, use_container_width=True):
            st.session_state.selected_zone = zone["zone_id"]
            st.rerun()

        st.markdown(
            f"**{zone['zone_id']}** — <span style='color:#fbbf24;'> {zone['label']} </span> | Priority {zone['priority']:.2f} | Confidence {zone['confidence']:.2f} | Uncertainty {zone['uncertainty']:.2f}",
            unsafe_allow_html=True,
        )
        st.caption(f"Detections: {zone['fire_count']} | Evidence: {', '.join(zone['evidence_factors'].keys())}")
        st.write(f"Reason: {zone['label']} for human review based on clustered detections and corroborating weather/incident signals.")

st.subheader("Resource Planning Suggestions")
st.caption(
    "Illustrative prototype estimates only, not dispatch orders. Detection density is based on satellite-point footprint, not population density. "
    "Confirm the fire perimeter, conditions, access, and resource needs with incident command."
)
resource_rows = []
for zone in queue:
    recommendation = build_resource_recommendations(zone)
    density = recommendation["detection_density_per_100_km2"]
    footprint = recommendation["estimated_footprint_km2"]
    density_text = (
        f"{density:.1f} detections / 100 km2 (footprint {footprint:.1f} km2)"
        if density is not None and footprint is not None
        else "Unavailable (need 2 distinct detection points)"
    )
    resource_rows.append({
        "Zone": zone["zone_id"],
        "Priority": zone["label"],
        "Firefighter planning range": recommendation["personnel_range"],
        "Estimated detection density": density_text,
        "Equipment to assess": "; ".join(recommendation["equipment"]),
    })
if resource_rows:
    st.dataframe(pd.DataFrame(resource_rows), width="stretch", hide_index=True)
else:
    st.info("No zone recommendations are available without fire detections.")

selected_zone = next((z for z in filtered_queue if z["zone_id"] == st.session_state.selected_zone), filtered_queue[0] if filtered_queue else None)
if selected_zone:
    st.subheader("Selected Zone Evidence")
    zone = selected_zone
    fire_df = pd.DataFrame(zone["detections"])
    weather_df = pd.DataFrame(zone["weather_records"])
    incident_df = pd.DataFrame(zone["incident_records"])
    st.write(f"Zone ID: {zone['zone_id']} | Priority: {zone['priority']:.2f} | Confidence: {zone['confidence']:.2f} | Uncertainty: {zone['uncertainty']:.2f}")
    evidence_tab, summary_tab, timeline_tab = st.tabs(["Evidence", "Evidence-Linked Situation Summary", "Timeline"])

    with evidence_tab:
        st.dataframe(fire_df[["id", "latitude", "longitude", "confidence", "frp", "timestamp"]], width="stretch")
        if not weather_df.empty:
            st.caption("Weather")
            st.dataframe(weather_df[["temperature_c", "humidity_pct", "wind_speed_kmh", "wind_direction_deg", "precipitation_mm", "source"]], width="stretch")
        if not incident_df.empty:
            st.caption("Incident reports")
            st.dataframe(incident_df[["id", "latitude", "longitude", "timestamp", "text", "source", "confidence"]], width="stretch")

    with summary_tab:
        st.write(generate_ai_summary(zone))

    with timeline_tab:
        if not fire_df.empty:
            ts = pd.to_datetime(fire_df["timestamp"], errors="coerce").dropna()
            if not ts.empty:
                counts = ts.value_counts().sort_index()
                fig = px.line(
                    x=[pd.Timestamp(v).strftime("%H:%M") for v in counts.index],
                    y=counts.values,
                    labels={"x": "Time", "y": "Detected fire activity over time"},
                    title="Detected fire activity over time"
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Timestamp data was not available for the sampled zone.")

st.subheader("Evaluation")
if fires.empty:
    st.write("Ground-truth labels were not available for this simulated prototype; quantitative detection performance could not be independently validated.")
else:
    st.write("Ground-truth labels were not available for this simulated prototype; quantitative detection performance could not be independently validated.")
    st.write("Prototype comparison: fire-only evidence vs. weather-only evidence vs. multimodal fusion is conceptual only as no calibrated ground truth is available.")

st.subheader("Dataset limitations")
st.markdown(
    "- Simulated incident reports are not operational observations.\n"
    "- Geographic coverage is limited to bundled sample data.\n"
    "- Temporal bias may exist in the sample window.\n"
    "- Satellite fire detections are subject to cloud cover and sensor thresholds.\n"
    "- Weather data may have limited temporal and spatial resolution.\n"
    "- Uncertainty in simulated data is intentionally high.\n"
    "- The prototype review-priority score is not operationally validated."
)

st.caption("This is a prototype uncertainty heuristic and is not a calibrated probability.")
