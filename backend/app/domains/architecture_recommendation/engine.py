"""Pure reference-topology loading and matching logic for the architecture recommendation
engine - independent of the ORM, same separation-of-concerns pattern as
app/domains/best_practice/engine.py. See reference/safe_pins.yaml for the data and the
disclaimer on where it does (and doesn't) come from.
"""

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


def load_pins() -> list[PinDefinition]:
    raw = yaml.safe_load((REFERENCE_DIR / "safe_pins.yaml").read_text())
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
