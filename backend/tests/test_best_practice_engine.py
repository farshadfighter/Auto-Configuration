from app.domains.best_practice import engine


def test_greater_than_with_missing_value_does_not_crash():
    # A rule YAML condition missing "value" (or set to null) must not raise - it should just
    # not match, rather than crashing the whole run with a TypeError comparing int and None.
    conditions = [{"field": "count", "operator": "greater_than"}]
    assert engine.evaluate_conditions({"count": 5}, conditions) is False


def test_less_than_with_missing_value_does_not_crash():
    conditions = [{"field": "count", "operator": "less_than"}]
    assert engine.evaluate_conditions({"count": 5}, conditions) is False


def test_greater_than_with_missing_actual_field_does_not_crash():
    conditions = [{"field": "missing_field", "operator": "greater_than", "value": 5}]
    assert engine.evaluate_conditions({}, conditions) is False


def test_greater_than_matches_when_both_sides_present():
    conditions = [{"field": "count", "operator": "greater_than", "value": 3}]
    assert engine.evaluate_conditions({"count": 5}, conditions) is True
