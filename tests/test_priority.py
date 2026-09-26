from services.priority import calculate_priority, priority_label


def test_priority_is_normalized_and_labelled():
    score = calculate_priority(fire=0.8, weather=0.7, incident=0.6, temporal=0.9)
    assert 0 <= score <= 1
    assert priority_label(score) in {"HIGH", "MEDIUM", "LOW"}


def test_priority_handles_missing_values():
    score = calculate_priority(fire=None, weather=0.5, incident=None, temporal=0.4)
    assert 0 <= score <= 1
