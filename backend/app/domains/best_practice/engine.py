"""Condition evaluator + YAML rule loader for the Best Practice / Architecture Validation
engine (spec sections 20, 25-31). Deliberately independent of application/ORM code (section 25:
"Best Practice Engine باید مستقل از Application Code باشد") - it only operates on plain dicts.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).parent / "rules"


@dataclass
class Rule:
    id: str
    technology: str
    category: str
    version: str
    severity: str
    title: str
    description: str
    applies_to: list[dict] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    recommendation: str = ""


def _get_field(context: dict, path: str) -> Any:
    value: Any = context
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


_OPERATORS = {
    "equals": lambda actual, expected: actual == expected,
    "not_equals": lambda actual, expected: actual != expected,
    "in": lambda actual, expected: actual in expected,
    "not_in": lambda actual, expected: actual not in expected,
    "exists": lambda actual, expected: actual is not None,
    "not_exists": lambda actual, expected: actual is None,
    "greater_than": lambda actual, expected: actual is not None and expected is not None and actual > expected,
    "less_than": lambda actual, expected: actual is not None and expected is not None and actual < expected,
}


def evaluate_conditions(context: dict, conditions: list[dict]) -> bool:
    """All conditions must hold (AND) for the list to match."""
    for condition in conditions:
        operator = _OPERATORS.get(condition["operator"])
        if operator is None:
            raise ValueError(f"Unknown rule operator: {condition['operator']}")
        actual = _get_field(context, condition["field"])
        if not operator(actual, condition.get("value")):
            return False
    return True


def load_rules() -> list[Rule]:
    rules = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        rules.append(
            Rule(
                id=raw["id"],
                technology=raw["technology"],
                category=raw["category"],
                version=str(raw.get("version", "1.0")),
                severity=raw["severity"],
                title=raw["title"],
                description=raw.get("description", ""),
                applies_to=raw.get("applies_to", []),
                conditions=raw["conditions"],
                recommendation=raw.get("recommendation", ""),
            )
        )
    return rules


def evaluate_rule_against_context(rule: Rule, context: dict) -> bool:
    """Returns True if this asset context VIOLATES the rule (i.e. a finding should be raised)."""
    if rule.applies_to and not evaluate_conditions(context, rule.applies_to):
        return False
    return evaluate_conditions(context, rule.conditions)
