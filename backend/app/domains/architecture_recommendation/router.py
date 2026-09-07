from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.architecture_recommendation import service
from app.domains.architecture_recommendation.schemas import SafeRecommendationRequest
from app.domains.audit.service import record_audit_event
from app.domains.design import service as design_service

router = APIRouter()


@router.post("/architecture-recommendations/safe", response_model=None, status_code=status.HTTP_201_CREATED)
def generate_safe_recommendation(
    payload: SafeRecommendationRequest, db: DbSession, current_user=Depends(require_permission("design.create"))
):
    design = service.generate_recommendation(db, name=payload.name, created_by=current_user.id)
    version = design_service.get_latest_version(db, design.id)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="SAFE_RECOMMENDATION_GENERATED",
        object_type="architecture_design",
        object_id=design.id,
        result="SUCCESS",
    )
    db.commit()
    return success({"design_id": str(design.id), "version_id": str(version.id), "name": design.name})
