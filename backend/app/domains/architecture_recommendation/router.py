from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.architecture_recommendation import service
from app.domains.architecture_recommendation.schemas import SafeRecommendationRequest
from app.domains.audit.service import record_audit_event
from app.domains.design import service as design_service

router = APIRouter()


@router.get("/architecture-recommendations/safe/path-analysis", response_model=None)
def get_path_analysis(db: DbSession, current_user=Depends(require_permission("topology.view"))):
    """Real, on-demand analysis: walks the actual topology graph between assets classified
    into adjacent SAFE zones and reports whether a real security device sits on the shortest
    real path between them. Stateless (recomputed every call) - see service.analyze_real_paths.
    """
    findings = service.analyze_real_paths(db)
    return success(
        [
            {
                "pin_a": f.pin_a,
                "pin_b": f.pin_b,
                "source_asset_id": str(f.source_asset_id),
                "source_asset_name": f.source_asset_name,
                "target_asset_id": str(f.target_asset_id),
                "target_asset_name": f.target_asset_name,
                "path_asset_ids": [str(a) for a in f.path_asset_ids],
                "path_asset_names": f.path_asset_names,
                "protected": f.protected,
                "required_capability": f.required_capability,
                "severity": f.severity,
            }
            for f in findings
        ]
    )


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
