from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.architecture_recommendation import service
from app.domains.architecture_recommendation.schemas import SafeRecommendationRequest
from app.domains.audit.service import record_audit_event
from app.domains.design import service as design_service

router = APIRouter()


def _serialize_scale_gap(g: service.ScaleGapFinding) -> dict:
    return {
        "pin": g.pin,
        "pin_label": g.pin_label,
        "component_type": g.component_type,
        "component_name": g.component_name,
        "metric_pin": g.metric_pin,
        "metric_asset_count": g.metric_asset_count,
        "existing_count": g.existing_count,
        "required_count": g.required_count,
    }


def _serialize_location_gap(g: service.LocationGapFinding) -> dict:
    return {
        "pin": g.pin,
        "pin_label": g.pin_label,
        "location_id": str(g.location_id),
        "location_name": g.location_name,
        "missing_component_type": g.missing_component_type,
        "missing_component_name": g.missing_component_name,
    }


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


@router.get("/architecture-recommendations/safe/scale-gaps", response_model=None)
def get_scale_gaps(db: DbSession, current_user=Depends(require_permission("topology.view"))):
    """Stateless, on-demand capacity/coverage gap report - independent of generating a new
    design, so it can be checked without leaving a trail of designs behind."""
    scale_gaps = service.compute_scale_gaps(db)
    location_gaps = service.compute_location_gaps(db)
    return success(
        {
            "scale_gaps": [_serialize_scale_gap(g) for g in scale_gaps],
            "location_gaps": [_serialize_location_gap(g) for g in location_gaps],
        }
    )


@router.post("/architecture-recommendations/safe", response_model=None, status_code=status.HTTP_201_CREATED)
def generate_safe_recommendation(
    payload: SafeRecommendationRequest, db: DbSession, current_user=Depends(require_permission("design.create"))
):
    design, scale_gaps, location_gaps = service.generate_recommendation(db, name=payload.name, created_by=current_user.id)
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
    return success(
        {
            "design_id": str(design.id),
            "version_id": str(version.id),
            "name": design.name,
            "scale_gaps": [_serialize_scale_gap(g) for g in scale_gaps],
            "location_gaps": [_serialize_location_gap(g) for g in location_gaps],
        }
    )
