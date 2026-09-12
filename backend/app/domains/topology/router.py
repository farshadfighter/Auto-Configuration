import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.topology import service
from app.domains.topology.schemas import (
    LayoutUpdate,
    TopologyGraph,
    TopologyLinkCreate,
    TopologyLinkOut,
    TopologyNodeCreate,
    TopologyNodeOut,
    TopologyViewOut,
)

router = APIRouter()


@router.get("/topology", response_model=None)
def get_topology(db: DbSession, sync: bool = True, current_user=Depends(require_permission("topology.view"))):
    if sync:
        service.sync_nodes_from_assets(db)
        service.sync_links_from_relationships(db)
        db.commit()
    nodes, links = service.get_full_topology(db)
    graph = TopologyGraph(
        nodes=[TopologyNodeOut.model_validate(n) for n in nodes],
        links=[TopologyLinkOut.model_validate(link) for link in links],
    )
    return success(graph.model_dump(mode="json"))


@router.get("/topology/views/{view_id}", response_model=None)
def get_view(view_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("topology.view"))):
    view = service.get_or_create_view(db, view_id)
    return success(TopologyViewOut.model_validate(view).model_dump(mode="json"))


@router.post("/topology/nodes", response_model=None, status_code=status.HTTP_201_CREATED)
def create_node(
    payload: TopologyNodeCreate, db: DbSession, current_user=Depends(require_permission("topology.edit"))
):
    node = service.create_node(db, payload.model_dump())
    record_audit_event(
        db, user_id=current_user.id, action="TOPOLOGY_NODE_CREATED", object_type="topology_node", object_id=node.id, result="SUCCESS"
    )
    db.commit()
    return success(TopologyNodeOut.model_validate(node).model_dump(mode="json"))


@router.post("/topology/links", response_model=None, status_code=status.HTTP_201_CREATED)
def create_link(
    payload: TopologyLinkCreate, db: DbSession, current_user=Depends(require_permission("topology.edit"))
):
    link = service.create_link(db, payload.model_dump())
    record_audit_event(
        db, user_id=current_user.id, action="TOPOLOGY_LINK_CREATED", object_type="topology_link", object_id=link.id, result="SUCCESS"
    )
    db.commit()
    return success(TopologyLinkOut.model_validate(link).model_dump(mode="json"))


@router.put("/topology/layout", response_model=None)
def update_layout(payload: LayoutUpdate, db: DbSession, current_user=Depends(require_permission("topology.edit"))):
    view = service.get_or_create_view(db, payload.view_id)
    service.update_layout(db, view.id, [p.model_dump() for p in payload.positions])
    db.commit()
    return success({"view_id": str(view.id), "updated": len(payload.positions)})


@router.post("/topology/validate", response_model=None)
def validate_topology(db: DbSession, current_user=Depends(require_permission("topology.view"))):
    findings = service.validate_topology(db)
    return success(findings)
