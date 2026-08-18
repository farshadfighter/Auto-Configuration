import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domains.assets.models import Asset, AssetRelationship
from app.domains.topology.models import TopologyLayout, TopologyLink, TopologyNode, TopologyNodeType, TopologyView


def sync_nodes_from_assets(db: Session) -> int:
    """Ensures every non-deleted asset has a corresponding topology node. Idempotent."""
    existing_refs = {
        n.reference_id
        for n in db.scalars(select(TopologyNode).where(TopologyNode.node_type == TopologyNodeType.DEVICE))
    }
    assets = list(db.scalars(select(Asset).where(Asset.deleted_at.is_(None))))
    created = 0
    for asset in assets:
        if asset.id in existing_refs:
            continue
        db.add(TopologyNode(node_type=TopologyNodeType.DEVICE, reference_id=asset.id, label=asset.name))
        created += 1
    db.flush()
    return created


def sync_links_from_relationships(db: Session) -> int:
    """Ensures a topology link exists for every connected_to asset relationship. Idempotent."""
    nodes_by_asset = {
        n.reference_id: n
        for n in db.scalars(select(TopologyNode).where(TopologyNode.node_type == TopologyNodeType.DEVICE))
    }
    existing_pairs = {
        (link.source_node_id, link.destination_node_id) for link in db.scalars(select(TopologyLink))
    }
    relationships = list(
        db.scalars(select(AssetRelationship).where(AssetRelationship.relationship_type == "connected_to"))
    )
    created = 0
    for rel in relationships:
        source_node = nodes_by_asset.get(rel.source_asset_id)
        dest_node = nodes_by_asset.get(rel.target_asset_id)
        if not source_node or not dest_node:
            continue
        if (source_node.id, dest_node.id) in existing_pairs or (dest_node.id, source_node.id) in existing_pairs:
            continue
        db.add(
            TopologyLink(
                source_node_id=source_node.id,
                destination_node_id=dest_node.id,
                link_type="connected_to",
                discovery_source=rel.discovery_source,
            )
        )
        created += 1
    db.flush()
    return created


def get_full_topology(db: Session) -> tuple[list[TopologyNode], list[TopologyLink]]:
    nodes = list(db.scalars(select(TopologyNode)))
    links = list(db.scalars(select(TopologyLink)))
    return nodes, links


def create_node(db: Session, data: dict) -> TopologyNode:
    node = TopologyNode(**data)
    db.add(node)
    db.flush()
    return node


def create_link(db: Session, data: dict) -> TopologyLink:
    for key in ("source_node_id", "destination_node_id"):
        if not db.get(TopologyNode, data[key]):
            raise NotFoundError("TOPOLOGY_NODE_NOT_FOUND", f"Topology node {data[key]} not found")
    link = TopologyLink(**data)
    db.add(link)
    db.flush()
    return link


def get_or_create_view(db: Session, view_id: uuid.UUID | None) -> TopologyView:
    if view_id:
        view = db.get(TopologyView, view_id)
        if not view:
            raise NotFoundError("TOPOLOGY_VIEW_NOT_FOUND", f"Topology view {view_id} not found")
        return view
    view = db.scalar(select(TopologyView).where(TopologyView.is_default.is_(True)))
    if view:
        return view
    view = TopologyView(name="Default Physical View", view_type="physical", is_default=True)
    db.add(view)
    db.flush()
    return view


def update_layout(db: Session, view_id: uuid.UUID, positions: list[dict]) -> None:
    get_or_create_view(db, view_id)
    existing = {
        row.node_id: row
        for row in db.scalars(select(TopologyLayout).where(TopologyLayout.view_id == view_id))
    }
    for pos in positions:
        node_id = pos["node_id"]
        if node_id in existing:
            existing[node_id].position_x = pos["x"]
            existing[node_id].position_y = pos["y"]
        else:
            db.add(TopologyLayout(view_id=view_id, node_id=node_id, position_x=pos["x"], position_y=pos["y"]))
    db.flush()


def validate_topology(db: Session) -> list[dict]:
    """Lightweight structural checks (spec section 20). Transient - not persisted as
    Architecture Findings; the Best Practice/Validation engine (Phase 3) owns persisted findings."""
    nodes, links = get_full_topology(db)
    degree: dict[uuid.UUID, int] = defaultdict(int)
    for link in links:
        degree[link.source_node_id] += 1
        degree[link.destination_node_id] += 1

    findings = []
    for node in nodes:
        node_degree = degree.get(node.id, 0)
        if node_degree == 0:
            findings.append(
                {
                    "code": "ORPHAN_ASSET",
                    "severity": "medium",
                    "node_id": str(node.id),
                    "message": f"'{node.label}' has no topology links (orphan).",
                }
            )
        elif node_degree == 1 and node.node_type == TopologyNodeType.DEVICE:
            findings.append(
                {
                    "code": "MISSING_REDUNDANCY",
                    "severity": "low",
                    "node_id": str(node.id),
                    "message": f"'{node.label}' has only a single link (possible single point of failure).",
                }
            )
    return findings
