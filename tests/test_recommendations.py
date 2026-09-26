from services.recommendations import build_resource_recommendations


def test_recommendations_include_planning_range_density_and_evidence_based_equipment():
    zone = {
        "priority": 0.8,
        "detections": [
            {"latitude": 17.385, "longitude": 78.486, "frp": 120},
            {"latitude": 17.405, "longitude": 78.500, "frp": 100},
        ],
        "weather_records": [{"wind_speed_kmh": 30}],
        "incident_records": [{"text": "Smoke reported"}],
    }

    recommendation = build_resource_recommendations(zone)

    assert recommendation["personnel_range"] == "8-12 (illustrative)"
    assert recommendation["estimated_footprint_km2"] > 0
    assert recommendation["detection_density_per_100_km2"] > 0
    assert any("engine and water" in item for item in recommendation["equipment"])
    assert any("wind shifts" in item for item in recommendation["equipment"])
    assert any("incident command" in item for item in recommendation["equipment"])


def test_density_is_unavailable_for_a_single_detection_point():
    recommendation = build_resource_recommendations({
        "priority": 0.2,
        "detections": [{"latitude": 17.385, "longitude": 78.486}],
    })

    assert recommendation["personnel_range"] == "2-4 (illustrative)"
    assert recommendation["estimated_footprint_km2"] is None
    assert recommendation["detection_density_per_100_km2"] is None


def test_no_detections_do_not_produce_a_staffing_estimate():
    recommendation = build_resource_recommendations({"priority": 0.9, "detections": []})

    assert recommendation["personnel_range"] == "Not estimated"
    assert recommendation["detection_density_per_100_km2"] is None