import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.architecture_recommendation import engine
from app.domains.assets.models import Asset, AssetRole, AssetType
from app.domains.design import service as design_service
from app.domains.design.models import ArchitectureDesign, DesignAssetMapping, DesignComponent, DesignMode, DesignRelationship
from app.domains.topology import service as topology_service
from app.domains.topology.models import TopologyLink, TopologyNode, TopologyNodeType

COLUMN_WIDTH = 260
ROW_HEIGHT = 110
DEFAULT_MAX_HOPS = 4


@dataclass
class AssetContext:
    asset: Asset
    type_code: str
    role_name: str | None


def _asset_contexts(db: Session) -> dict[uuid.UUID, AssetContext]:
    """Every non-deleted asset, keyed by id, with its asset_type code and role name attached -
    both needed for engine.asset_satisfies_component matching. Used both for PIN grouping and
    for identifying assets that sit as intermediate hops on a real topology path."""
    rows = db.execute(
        select(Asset, AssetType.code, AssetRole.name)
        .join(AssetType, Asset.asset_type_id == AssetType.id)
        .outerjoin(AssetRole, Asset.role_id == AssetRole.id)
        .where(Asset.deleted_at.is_(None))
    )
    return {asset.id: AssetContext(asset, type_code, role_name) for asset, type_code, role_name in rows}


def _assets_by_pin(db: Session, contexts: dict[uuid.UUID, AssetContext] | None = None) -> dict[str, list[tuple[Asset, str, str | None]]]:
    """Classified assets (Asset.safe_pin set) grouped by that pin."""
    contexts = contexts if contexts is not None else _asset_contexts(db)
    grouped: dict[str, list[tuple[Asset, str, str | None]]] = {}
    for ctx in contexts.values():
        if ctx.asset.safe_pin is not None:
            grouped.setdefault(ctx.asset.safe_pin.value, []).append((ctx.asset, ctx.type_code, ctx.role_name))
    return grouped


def _topology_adjacency(db: Session) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, list[uuid.UUID]]]:
    """Syncs topology from the current asset/relationship state (same as the Topology page and
    the best-practice engine do before reading it, so this reflects reality even if nobody has
    opened the Topology page recently), then returns (node_id -> asset_id, node_id -> [neighbor
    node_id, ...]) for real, currently-linked DEVICE nodes."""
    topology_service.sync_nodes_from_assets(db)
    topology_service.sync_links_from_relationships(db)
    db.flush()

    nodes = list(db.scalars(select(TopologyNode).where(TopologyNode.node_type == TopologyNodeType.DEVICE)))
    node_to_asset = {n.id: n.reference_id for n in nodes}
    adjacency: dict[uuid.UUID, list[uuid.UUID]] = {n.id: [] for n in nodes}
    for link in db.scalars(select(TopologyLink)):
        if link.source_node_id in adjacency and link.destination_node_id in adjacency:
            adjacency[link.source_node_id].append(link.destination_node_id)
            adjacency[link.destination_node_id].append(link.source_node_id)
    return node_to_asset, adjacency


@dataclass
class PathFinding:
    pin_a: str
    pin_b: str
    source_asset_id: uuid.UUID
    source_asset_name: str
    target_asset_id: uuid.UUID
    target_asset_name: str
    path_asset_ids: list[uuid.UUID]
    path_asset_names: list[str]
    protected: bool
    required_capability: str
    severity: str


def analyze_real_paths(db: Session, *, max_hops: int = DEFAULT_MAX_HOPS) -> list[PathFinding]:
    """For every SAFE security boundary (e.g. 'there should be a firewall between Internet Edge
    and Campus Core'), walks the REAL topology graph - actual TopologyLink connectivity between
    assets the user has classified into those two PINs - and checks whether a capable device
    (matching the boundary's required_capability) actually sits on the real, shortest path
    between them. This is materially different from generate_recommendation's per-PIN
    "do we own one of these somewhere" check: an org can own a firewall and still have an
    unprotected real path if that firewall isn't actually positioned between the two zones.
    Pairs with no real path within max_hops are skipped entirely - that means "not connected
    yet", not a finding."""
    boundaries = engine.load_security_boundaries()
    if not boundaries:
        return []

    pins = engine.load_pins()
    contexts = _asset_contexts(db)
    assets_by_pin = _assets_by_pin(db, contexts)
    node_to_asset, adjacency = _topology_adjacency(db)
    asset_to_node: dict[uuid.UUID, uuid.UUID] = {asset_id: node_id for node_id, asset_id in node_to_asset.items()}

    findings: list[PathFinding] = []
    for boundary in boundaries:
        capability = engine.capability_matcher(pins, boundary.requires_capability)
        pin_a_assets = assets_by_pin.get(boundary.pin_a, [])
        pin_b_assets = assets_by_pin.get(boundary.pin_b, [])

        for asset_a, _, _ in pin_a_assets:
            node_a = asset_to_node.get(asset_a.id)
            if node_a is None:
                continue
            for asset_b, _, _ in pin_b_assets:
                node_b = asset_to_node.get(asset_b.id)
                if node_b is None or node_a == node_b:
                    continue

                path_node_ids = engine.shortest_path(adjacency, node_a, node_b, max_hops)
                if path_node_ids is None:
                    continue

                path_asset_ids = [node_to_asset[nid] for nid in path_node_ids]
                path_asset_names = []
                protected = False
                for asset_id in path_asset_ids:
                    ctx = contexts.get(asset_id)
                    if ctx is None:
                        continue
                    path_asset_names.append(ctx.asset.name)
                    if engine.asset_satisfies_component(
                        capability, asset_type_code=ctx.type_code, role_name=ctx.role_name, asset_name=ctx.asset.name
                    ):
                        protected = True

                findings.append(
                    PathFinding(
                        pin_a=boundary.pin_a,
                        pin_b=boundary.pin_b,
                        source_asset_id=asset_a.id,
                        source_asset_name=asset_a.name,
                        target_asset_id=asset_b.id,
                        target_asset_name=asset_b.name,
                        path_asset_ids=path_asset_ids,
                        path_asset_names=path_asset_names,
                        protected=protected,
                        required_capability=boundary.requires_capability,
                        severity=boundary.severity,
                    )
                )
    return findings


def _unprotected_capabilities_by_pin(path_findings: list[PathFinding]) -> dict[str, set[str]]:
    """pin_id -> set of capability types that have at least one real, unprotected boundary
    crossing at that pin and no protected crossing to offset it. Used to override the naive
    "do we own one of these somewhere in the PIN" check in generate_recommendation: owning a
    firewall doesn't help if it isn't actually positioned on the real path to the next zone."""
    protected: dict[tuple[str, str, str], bool] = {}
    for f in path_findings:
        key = (f.pin_a, f.pin_b, f.required_capability)
        protected[key] = protected.get(key, False) or f.protected

    by_pin: dict[str, set[str]] = {}
    for (pin_a, pin_b, capability), is_protected in protected.items():
        if is_protected:
            continue
        by_pin.setdefault(pin_a, set()).add(capability)
        by_pin.setdefault(pin_b, set()).add(capability)
    return by_pin


def generate_recommendation(db: Session, *, name: str, created_by: uuid.UUID | None) -> ArchitectureDesign:
    """Builds a new Architecture Design pre-populated with a SAFE-inspired reference topology,
    grounded in whatever of the current asset inventory has been classified by Place in the
    Network (Asset.safe_pin). Existing assets appear as real components (mapped back to the
    asset); reference roles the inventory doesn't yet cover appear as recommended-but-missing
    components so the gap is visible directly in the generated diagram.

    Presence of a matching asset type in a PIN isn't enough on its own for a security
    capability (firewall, NAC) that guards a boundary to another PIN: real path analysis
    (analyze_real_paths) can show that capability isn't actually positioned on the real path
    between the two zones, in which case it's still rendered as a recommended/missing gap even
    though an asset of that type technically exists somewhere in the PIN."""
    pins = engine.load_pins()
    assets_by_pin = _assets_by_pin(db)
    path_findings = analyze_real_paths(db)
    unprotected_by_pin = _unprotected_capabilities_by_pin(path_findings)

    design = design_service.create_design(
        db,
        name=name,
        description=(
            "Auto-generated from the current asset inventory using a SAFE-inspired Places-in-"
            "the-Network reference model. Dashed components are recommended roles not yet "
            "covered by a classified asset, OR a security capability that exists but isn't "
            "actually positioned on the real topology path between zones (see the path "
            "analysis panel)."
        ),
        mode=DesignMode.BEST_PRACTICE_ASSISTED,
        created_by=created_by,
    )
    version = design_service.get_latest_version(db, design.id)

    component_by_pin_first: dict[str, uuid.UUID] = {}

    for pin in pins:
        pin_assets = assets_by_pin.get(pin.id, [])
        # Capabilities this PIN owns an asset for, but real path analysis shows aren't actually
        # protecting the boundary - force these to stay in the "recommended" set below.
        unprotected_here = unprotected_by_pin.get(pin.id, set())
        satisfied_component_types: set[str] = set()
        row = 0

        for asset, type_code, role_name in pin_assets:
            component = DesignComponent(
                design_version_id=version.id,
                component_type=type_code,
                name=asset.name,
                properties={"safe_pin": pin.id, "recommended": False},
                position={"x": pin.order * COLUMN_WIDTH, "y": row * ROW_HEIGHT},
            )
            db.add(component)
            db.flush()
            db.add(DesignAssetMapping(design_component_id=component.id, asset_id=asset.id))
            component_by_pin_first.setdefault(pin.id, component.id)
            row += 1

            for rc in pin.recommended_components:
                if rc.component_type in satisfied_component_types or rc.component_type in unprotected_here:
                    continue
                if engine.asset_satisfies_component(rc, asset_type_code=type_code, role_name=role_name, asset_name=asset.name):
                    satisfied_component_types.add(rc.component_type)

        for rc in pin.recommended_components:
            if rc.component_type in satisfied_component_types:
                continue
            properties = {"safe_pin": pin.id, "recommended": True}
            if rc.component_type in unprotected_here:
                properties["reason"] = "unprotected_path"
            component = DesignComponent(
                design_version_id=version.id,
                component_type=rc.component_type,
                name=rc.name,
                properties=properties,
                position={"x": pin.order * COLUMN_WIDTH, "y": row * ROW_HEIGHT},
            )
            db.add(component)
            db.flush()
            component_by_pin_first.setdefault(pin.id, component.id)
            row += 1

    for pin in pins:
        source_id = component_by_pin_first.get(pin.id)
        if not source_id:
            continue
        for target_pin_id in pin.connects_to:
            target_id = component_by_pin_first.get(target_pin_id)
            if not target_id:
                continue
            db.add(
                DesignRelationship(
                    design_version_id=version.id,
                    source_component_id=source_id,
                    target_component_id=target_id,
                    relationship_type="connects_to",
                )
            )

    db.flush()
    return design
