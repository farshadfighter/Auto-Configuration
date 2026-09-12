import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response

from app.api.deps import DbSession, require_permission
from app.core.errors import ValidationAppError
from app.core.responses import success
from app.domains.assets import csv_transfer, service
from app.domains.assets.schemas import (
    AssetCreate,
    AssetOut,
    AssetRelationshipCreate,
    AssetRelationshipOut,
    AssetTypeCreate,
    AssetTypeOut,
    AssetUpdate,
    ComplianceFrameworkOut,
)
from app.domains.audit.service import record_audit_event

router = APIRouter()


@router.get("/asset-types", response_model=None)
def list_asset_types(db: DbSession, current_user=Depends(require_permission("asset.view"))):
    asset_types = service.list_asset_types(db)
    return success([AssetTypeOut.model_validate(t).model_dump(mode="json") for t in asset_types])


@router.get("/compliance-frameworks", response_model=None)
def list_compliance_frameworks(db: DbSession, current_user=Depends(require_permission("asset.view"))):
    frameworks = service.list_compliance_frameworks(db)
    return success([ComplianceFrameworkOut.model_validate(f).model_dump(mode="json") for f in frameworks])


@router.post("/asset-types", response_model=None, status_code=status.HTTP_201_CREATED)
def create_asset_type(payload: AssetTypeCreate, db: DbSession, current_user=Depends(require_permission("asset.create"))):
    asset_type = service.create_asset_type(db, code=payload.code, name=payload.name, category=payload.category)
    db.commit()
    return success(AssetTypeOut.model_validate(asset_type).model_dump(mode="json"))


@router.get("/assets", response_model=None)
def list_assets(
    db: DbSession,
    page: int = 1,
    page_size: int = 50,
    site_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
    managed: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    current_user=Depends(require_permission("asset.view")),
):
    items, total = service.list_assets(
        db,
        page=page,
        page_size=page_size,
        site_id=site_id,
        environment_id=environment_id,
        managed=managed,
        status=status_filter,
        search=search,
    )
    data = [AssetOut.model_validate(a).model_dump(mode="json") for a in items]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})


@router.post("/assets", response_model=None, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: DbSession, current_user=Depends(require_permission("asset.create"))):
    asset = service.create_asset(db, payload.model_dump())
    record_audit_event(
        db,
        user_id=current_user.id,
        action="ASSET_CREATED",
        object_type="asset",
        object_id=asset.id,
        result="SUCCESS",
        new_value={"asset_code": asset.asset_code, "name": asset.name},
    )
    db.commit()
    return success(AssetOut.model_validate(asset).model_dump(mode="json"))


@router.get("/assets/export/csv", response_model=None)
def export_assets_csv(
    db: DbSession,
    site_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
    managed: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    current_user=Depends(require_permission("asset.view")),
):
    assets = service.list_assets_for_export(
        db, site_id=site_id, environment_id=environment_id, managed=managed, status=status_filter, search=search
    )
    csv_content = csv_transfer.export_assets_to_csv(db, assets)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assets_export.csv"},
    )


@router.post("/assets/import/csv", response_model=None)
async def import_assets_csv(db: DbSession, current_user=Depends(require_permission("asset.create")), file: UploadFile = File(...)):
    raw = await file.read()
    try:
        csv_content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationAppError("INVALID_CSV_ENCODING", "CSV file must be UTF-8 encoded")

    summary = csv_transfer.import_assets_from_csv(db, csv_content)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="ASSETS_CSV_IMPORTED",
        object_type="asset_csv_import",
        object_id=uuid.uuid4(),
        result="SUCCESS",
        new_value={"created": summary.created, "updated": summary.updated, "error_count": len(summary.errors)},
    )
    db.commit()
    return success({"created": summary.created, "updated": summary.updated, "errors": summary.errors})


@router.get("/assets/{asset_id}", response_model=None)
def get_asset(asset_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("asset.view"))):
    asset = service.get_asset(db, asset_id)
    return success(AssetOut.model_validate(asset).model_dump(mode="json"))


@router.put("/assets/{asset_id}", response_model=None)
def update_asset(
    asset_id: uuid.UUID, payload: AssetUpdate, db: DbSession, current_user=Depends(require_permission("asset.edit"))
):
    before = service.get_asset(db, asset_id)
    before_snapshot = {"name": before.name, "status": before.status.value}
    asset = service.update_asset(db, asset_id, payload.model_dump(exclude_unset=True))
    record_audit_event(
        db,
        user_id=current_user.id,
        action="ASSET_UPDATED",
        object_type="asset",
        object_id=asset.id,
        result="SUCCESS",
        old_value=before_snapshot,
        new_value={"name": asset.name, "status": asset.status.value},
    )
    db.commit()
    return success(AssetOut.model_validate(asset).model_dump(mode="json"))


@router.delete("/assets/{asset_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("asset.delete"))):
    service.soft_delete_asset(db, asset_id)
    record_audit_event(
        db, user_id=current_user.id, action="ASSET_DELETED", object_type="asset", object_id=asset_id, result="SUCCESS"
    )
    db.commit()
    return None


@router.get("/assets/{asset_id}/relationships", response_model=None)
def list_relationships(
    asset_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("asset.view"))
):
    relationships = service.list_relationships(db, asset_id)
    return success([AssetRelationshipOut.model_validate(r).model_dump(mode="json") for r in relationships])


@router.post("/assets/relationships", response_model=None, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: AssetRelationshipCreate, db: DbSession, current_user=Depends(require_permission("asset.edit"))
):
    relationship = service.create_relationship(db, payload.model_dump())
    record_audit_event(
        db,
        user_id=current_user.id,
        action="ASSET_RELATIONSHIP_CREATED",
        object_type="asset_relationship",
        object_id=relationship.id,
        result="SUCCESS",
    )
    db.commit()
    return success(AssetRelationshipOut.model_validate(relationship).model_dump(mode="json"))
