from app.domains.best_practice import engine


def _rule(rule_id: str) -> engine.Rule:
    return next(r for r in engine.load_rules() if r.id == rule_id)


def test_backup_required_without_frequency_violates_bp_asset_004():
    rule = _rule("BP-ASSET-004")
    violating = {"asset": {"backup_required": True, "backup_frequency": None}}
    compliant = {"asset": {"backup_required": True, "backup_frequency": "daily"}}
    not_applicable = {"asset": {"backup_required": False, "backup_frequency": None}}
    assert engine.evaluate_rule_against_context(rule, violating) is True
    assert engine.evaluate_rule_against_context(rule, compliant) is False
    assert engine.evaluate_rule_against_context(rule, not_applicable) is False


def test_asset_nearing_retirement_violates_bp_asset_005():
    rule = _rule("BP-ASSET-005")
    violating = {"asset": {"status": "active", "days_until_retirement": 30}}
    past_due = {"asset": {"status": "active", "days_until_retirement": -5}}
    compliant = {"asset": {"status": "active", "days_until_retirement": 365}}
    no_date_set = {"asset": {"status": "active", "days_until_retirement": None}}
    assert engine.evaluate_rule_against_context(rule, violating) is True
    assert engine.evaluate_rule_against_context(rule, past_due) is True
    assert engine.evaluate_rule_against_context(rule, compliant) is False
    assert engine.evaluate_rule_against_context(rule, no_date_set) is False


def test_confidential_asset_without_risk_ref_violates_bp_isms_001():
    rule = _rule("BP-ISMS-001")
    violating = {"asset": {"information_classification": "restricted", "risk_assessment_ref": None}}
    compliant = {"asset": {"information_classification": "restricted", "risk_assessment_ref": "RA-2026-014"}}
    not_applicable = {"asset": {"information_classification": "internal", "risk_assessment_ref": None}}
    assert engine.evaluate_rule_against_context(rule, violating) is True
    assert engine.evaluate_rule_against_context(rule, compliant) is False
    assert engine.evaluate_rule_against_context(rule, not_applicable) is False


def test_domain_controller_without_redundant_link_violates_bp_ms_ad_001():
    rule = _rule("BP-MS-AD-001")
    violating = {"asset": {"asset_type_code": "domain_controller"}, "topology": {"degree": 1}}
    compliant = {"asset": {"asset_type_code": "domain_controller"}, "topology": {"degree": 2}}
    not_applicable = {"asset": {"asset_type_code": "server"}, "topology": {"degree": 1}}
    assert engine.evaluate_rule_against_context(rule, violating) is True
    assert engine.evaluate_rule_against_context(rule, compliant) is False
    assert engine.evaluate_rule_against_context(rule, not_applicable) is False


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
