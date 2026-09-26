from services.data_loader import load_fire_data, load_weather_data, load_incident_data


def test_load_fire_data_has_expected_columns():
    fires = load_fire_data()
    assert not fires.empty
    assert {"latitude", "longitude", "confidence", "frp", "timestamp"}.issubset(set(fires.columns))
    assert fires["confidence"].between(0, 1).all()


def test_weather_and_incident_data_are_loaded():
    weather = load_weather_data()
    incidents = load_incident_data()
    assert not weather.empty
    assert not incidents.empty
    assert incidents["text"].notna().all()
