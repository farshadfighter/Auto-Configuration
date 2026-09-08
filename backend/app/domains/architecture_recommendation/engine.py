"""Pure reference-topology loading and matching logic for the architecture recommendation
engine - independent of the ORM, same separation-of-concerns pattern as
app/domains/best_practice/engine.py. See reference/safe_pins.yaml for the data and the
disclaimer on where it does (and doesn't) come from.
"""

import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REFERENCE_DIR = Path(__file__).parent / "reference"


@dataclass
class RecommendedComponent:
    component_type: str
    name: str
    matches_asset_type_codes: list[str] = field(default_factory=list)
    matches_keywords: list[str] = field(default_factory=list)


@dataclass
class PinDefinition:
    id: str
    label: str
    order: int
    connects_to: list[str]
    recommended_components: list[RecommendedComponent]
    cross_cutting: bool = False


@dataclass
class SecurityBoundary:
    pin_a: str
    pin_b: str
    requires_capability: str
    severity: str


def _load_raw() -> dict:
    return yaml.safe_load((REFERENCE_DIR / "safe_pins.yaml").read_text())


def load_pins() -> list[PinDefinition]:
    raw = _load_raw()
    pins = []
    for p in raw["pins"]:
        components = [
            RecommendedComponent(
                component_type=c["component_type"],
                name=c["name"],
                matches_asset_type_codes=c.get("matches_asset_type_codes", []),
                matches_keywords=c.get("matches_keywords", []),
            )
            for c in p["recommended_components"]
        ]
        pins.append(
            PinDefinition(
                id=p["id"],
                label=p["label"],
                order=p["order"],
                connects_to=p.get("connects_to", []),
                recommended_components=components,
                cross_cutting=p.get("cross_cutting", False),
            )
        )
    return sorted(pins, key=lambda pin: pin.order)


def load_security_boundaries() -> list[SecurityBoundary]:
    raw = _load_raw()
    return [
        SecurityBoundary(
            pin_a=b["between"][0], pin_b=b["between"][1], requires_capability=b["requires_capability"], severity=b["severity"]
        )
        for b in raw.get("security_boundaries", [])
    ]


def capability_matcher(pins: list[PinDefinition], component_type: str) -> RecommendedComponent:
    """Merges matching criteria for a capability (e.g. 'firewall') across every PIN that
    defines a recommended component of that type, so path analysis can check 'does this asset
    provide capability X' independent of which PIN it happens to be classified into."""
    type_codes: set[str] = set()
    keywords: set[str] = set()
    name = component_type
    for pin in pins:
        for rc in pin.recommended_components:
            if rc.component_type == component_type:
                type_codes.update(rc.matches_asset_type_codes)
                keywords.update(rc.matches_keywords)
                name = rc.name
    return RecommendedComponent(
        component_type=component_type, name=name, matches_asset_type_codes=list(type_codes), matches_keywords=list(keywords)
    )


def shortest_path(adjacency: dict[uuid.UUID, list[uuid.UUID]], start: uuid.UUID, goal: uuid.UUID, max_hops: int) -> list[uuid.UUID] | None:
    """Plain BFS over a real (already-built) topology adjacency graph - the shortest real
    route between two nodes, capped at max_hops, or None if they aren't connected within that
    many hops (which just means "not cabled/discovered yet", not a finding in itself)."""
    if start not in adjacency or goal not in adjacency:
        return None
    if start == goal:
        return [start]
    visited = {start}
    queue: deque[list[uuid.UUID]] = deque([[start]])
    while queue:
        path = queue.popleft()
        if len(path) - 1 >= max_hops:
            continue
        for neighbor in adjacency.get(path[-1], []):
            if neighbor in visited:
                continue
            next_path = path + [neighbor]
            if neighbor == goal:
                return next_path
            visited.add(neighbor)
            queue.append(next_path)
    return None


def asset_satisfies_component(
    component: RecommendedComponent, *, asset_type_code: str, role_name: str | None, asset_name: str
) -> bool:
    """Does this asset already cover a recommended role? Matches on asset type code first
    (reliable, closed vocabulary), falling back to a case-insensitive substring match of the
    component's keywords against the asset's role name + asset name (free text, best-effort)."""
    if asset_type_code in component.matches_asset_type_codes:
        return True
    haystack = f"{role_name or ''} {asset_name}".lower()
    return any(keyword.lower() in haystack for keyword in component.matches_keywords)
