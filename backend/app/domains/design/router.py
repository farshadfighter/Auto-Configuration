import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.design import service
from app.domains.design.schemas import (
    ApproveDesignRequest,
    AssetMappingRequest,
    ComponentCreate,
    ComponentOut,
    DesignCreate,
    DesignOut,
    DesignVersionOut,
    RecommendationMappingRequest,
    RelationshipCreate,
    RelationshipOut,
    VersionGraph,
)

router = APIRouter()


class DesignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.post("/designs", response_model=None, status_code=status.HTTP_201_CREATED)
def create_design(payload: DesignCreate, db: DbSession, current_user=Depends(require_permission("design.create"))):
    design = service.create_design(
        db, name=payload.name, description=payload.description, mode=payload.mode, created_by=current_user.id
    )
    record_audit_event(
        db, user_id=current_user.id, action="DESIGN_CREATED", object_type="architecture_design", object_id=design.id, result="SUCCESS"
    )
    db.commit()
    return success(DesignOut.model_validate(design).model_dump(mode="json"))


@router.get("/designs", response_model=None)
def list_designs(db: DbSession, page: int = 1, page_size: int = 50, current_user=Depends(require_permission("design.view"))):
    items, total = service.list_designs(db, page=page, page_size=page_size)
    data = [DesignOut.model_validate(d).model_dump(mode="json") for d in items]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})


@router.get("/designs/{design_id}", response_model=None)
def get_design(design_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("design.view"))):
    design = service.get_design(db, design_id)
    latest = service.get_latest_version(db, design_id)
    data = DesignOut.model_validate(design).model_dump(mode="json")
    data["latest_version"] = DesignVersionOut.model_validate(latest).model_dump(mode="json")
    return success(data)


@router.put("/designs/{design_id}", response_model=None)
def update_design(design_id: uuid.UUID, payload: DesignUpdate, db: DbSession, current_user=Depends(require_permission("design.edit"))):
    design = service.get_design(db, design_id)
    if payload.name is not None:
        design.name = payload.name
    if payload.description is not None:
        design.description = payload.description
    db.commit()
    return success(DesignOut.model_validate(design).model_dump(mode="json"))


@router.post("/designs/{design_id}/versions", response_model=None, status_code=status.HTTP_201_CREATED)
def create_version(design_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("design.edit"))):
    version = service.create_new_version(db, design_id, current_user.id)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="DESIGN_VERSION_CREATED",
        object_type="architecture_design_version",
        object_id=version.id,
        result="SUCCESS",
        new_value={"version_label": version.version_label},
    )
    db.commit()
    return success(DesignVersionOut.model_validate(version).model_dump(mode="json"))


@router.post("/designs/{design_id}/approve", response_model=None)
def approve_design(
    design_id: uuid.UUID, payload: ApproveDesignRequest, db: DbSession, current_user=Depends(require_permission("design.approve"))
):
    version = service.approve_design(db, design_id, current_user.id, payload.comment)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="DESIGN_APPROVED",
        object_type="architecture_design_version",
        object_id=version.id,
        result="SUCCESS",
        new_value={"version_label": version.version_label, "comment": payload.comment},
    )
    db.commit()
    return success(DesignVersionOut.model_validate(version).model_dump(mode="json"))


@router.get("/designs/versions/{version_id}", response_model=None)
def get_version_graph(version_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("design.view"))):
    components, relationships = service.get_version_graph(db, version_id)
    graph = VersionGraph(
        components=[ComponentOut.model_validate(c) for c in components],
        relationships=[RelationshipOut.model_validate(r) for r in relationships],
    )
    return success(graph.model_dump(mode="json"))


@router.post("/designs/versions/{version_id}/components", response_model=None, status_code=status.HTTP_201_CREATED)
def add_component(
    version_id: uuid.UUID, payload: ComponentCreate, db: DbSession, current_user=Depends(require_permission("design.edit"))
):
    component = service.add_component(db, version_id, payload.model_dump())
    db.commit()
    return success(ComponentOut.model_validate(component).model_dump(mode="json"))


@router.post("/designs/versions/{version_id}/relationships", response_model=None, status_code=status.HTTP_201_CREATED)
def add_relationship(
    version_id: uuid.UUID, payload: RelationshipCreate, db: DbSession, current_user=Depends(require_permission("design.edit"))
):
    relationship = service.add_relationship(db, version_id, payload.model_dump())
    db.commit()
    return success(RelationshipOut.model_validate(relationship).model_dump(mode="json"))


@router.post("/designs/components/{component_id}/map-asset", response_model=None)
def map_asset(
    component_id: uuid.UUID, payload: AssetMappingRequest, db: DbSession, current_user=Depends(require_permission("design.edit"))
):
    service.map_component_to_asset(db, component_id, payload.asset_id)
    db.commit()
    return success({"component_id": str(component_id), "asset_id": str(payload.asset_id)})


@router.post("/designs/versions/{version_id}/map-recommendation", response_model=None)
def map_recommendation(
    version_id: uuid.UUID, payload: RecommendationMappingRequest, db: DbSession, current_user=Depends(require_permission("design.edit"))
):
    service.map_recommendation(db, version_id, payload.finding_id)
    db.commit()
    return success({"version_id": str(version_id), "finding_id": str(payload.finding_id)})
