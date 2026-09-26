from services.fusion import build_zones, build_review_queue


def test_zone_generation_creates_priority_data():
    zones = build_zones()
    assert len(zones) > 0
    assert all("priority" in zone for zone in zones)
    assert all("confidence" in zone for zone in zones)


def test_review_queue_orders_by_priority_desc():
    zones = build_review_queue()
    assert len(zones) > 1
    priorities = [zone["priority"] for zone in zones]
    assert priorities == sorted(priorities, reverse=True)
