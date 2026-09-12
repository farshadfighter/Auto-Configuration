import uuid

import pytest

from app.domains.configuration import engine
from app.drivers.base import ChangeType


def test_topological_order_linear_chain():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    order = engine.topological_order([a, b, c], [(a, b), (b, c)])
    assert order == [a, b, c]


def test_topological_order_diamond():
    a, b, c, d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    order = engine.topological_order([a, b, c, d], [(a, b), (a, c), (b, d), (c, d)])
    assert order.index(a) < order.index(b)
    assert order.index(a) < order.index(c)
    assert order.index(b) < order.index(d)
    assert order.index(c) < order.index(d)


def test_topological_order_detects_cycle():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with pytest.raises(engine.DependencyCycleError):
        engine.topological_order([a, b, c], [(a, b), (b, c), (c, a)])


def test_compute_change_type_create_when_no_current_state():
    assert engine.compute_change_type(None, {"vlan_id": 10}) == ChangeType.CREATE


def test_compute_change_type_no_change_when_states_match():
    assert engine.compute_change_type({"vlan_id": 10, "name": "x"}, {"vlan_id": 10, "name": "x"}) == ChangeType.NO_CHANGE


def test_compute_change_type_update_when_states_differ():
    assert engine.compute_change_type({"vlan_id": 10, "name": "old"}, {"vlan_id": 10, "name": "new"}) == ChangeType.UPDATE


def test_diff_fields_reports_only_changed_keys():
    diff = engine.diff_fields({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
    fields = {d["field"] for d in diff}
    assert fields == {"b", "c"}
