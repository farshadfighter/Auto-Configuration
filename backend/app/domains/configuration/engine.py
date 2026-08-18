"""Dependency-graph resolution and desired-state diff logic (spec sections 28-30, 43).
Pure functions - no DB/ORM access - so they're trivially unit-testable.
"""

import uuid

from app.drivers.base import ChangeType


class DependencyCycleError(Exception):
    pass


def topological_order(object_ids: list[uuid.UUID], edges: list[tuple[uuid.UUID, uuid.UUID]]) -> list[uuid.UUID]:
    """Kahn's algorithm. edges are (parent, child) meaning parent must execute before child.
    Raises DependencyCycleError if the graph has a cycle (spec section 28)."""
    in_degree = dict.fromkeys(object_ids, 0)
    children: dict[uuid.UUID, list[uuid.UUID]] = {oid: [] for oid in object_ids}
    for parent, child in edges:
        children[parent].append(child)
        in_degree[child] += 1

    queue = sorted([oid for oid, deg in in_degree.items() if deg == 0], key=str)
    ordered: list[uuid.UUID] = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for child in sorted(children[current], key=str):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(ordered) != len(object_ids):
        raise DependencyCycleError("Configuration object dependency graph contains a cycle")
    return ordered


def compute_change_type(current_state: dict | None, desired_state: dict) -> ChangeType:
    if current_state is None:
        return ChangeType.CREATE
    if _normalize(current_state) == _normalize(desired_state):
        return ChangeType.NO_CHANGE
    return ChangeType.UPDATE


def _normalize(state: dict) -> dict:
    """Ignores bookkeeping keys (e.g. raw device output) that aren't part of desired intent."""
    return {k: v for k, v in state.items() if k != "raw"}


def diff_fields(current_state: dict | None, desired_state: dict) -> list[dict]:
    current = _normalize(current_state or {})
    desired = _normalize(desired_state)
    changes = []
    for key in sorted(set(current) | set(desired)):
        before, after = current.get(key), desired.get(key)
        if before != after:
            changes.append({"field": key, "before": before, "after": after})
    return changes
