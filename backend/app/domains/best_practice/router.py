import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.service import record_audit_event
from app.domains.best_practice import service
from app.domains.best_practice.schemas import ArchitectureFindingOut, BestPracticeRunOut, IgnoreFindingRequest

router = APIRouter()


def _finding_out(db: DbSession, finding) -> dict:
    data = ArchitectureFindingOut.model_validate(finding).model_dump(mode="json")
    data["affected_asset_ids"] = [str(a) for a in service.get_finding_asset_ids(db, finding.id)]
    return data


@router.post("/best-practice/analyze", response_model=None, status_code=status.HTTP_201_CREATED)
def analyze(db: DbSession, current_user=Depends(require_permission("best_practice.run"))):
    run = service.run_analysis(db, triggered_by=current_user.id)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="BEST_PRACTICE_ANALYSIS_RUN",
        object_type="best_practice_run",
        object_id=run.id,
        result="SUCCESS",
        new_value={"findings_created": run.findings_created, "rules_evaluated": run.rules_evaluated},
    )
    db.commit()
    return success(BestPracticeRunOut.model_validate(run).model_dump(mode="json"))


@router.get("/best-practice/findings", response_model=None)
def list_findings(
    db: DbSession,
    status_filter: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user=Depends(require_permission("best_practice.view")),
):
    items, total = service.list_findings(db, status=status_filter, severity=severity, page=page, page_size=page_size)
    data = [_finding_out(db, f) for f in items]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})


@router.get("/best-practice/findings/{finding_id}", response_model=None)
def get_finding(
    finding_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("best_practice.view"))
):
    finding = service.get_finding(db, finding_id)
    return success(_finding_out(db, finding))


@router.post("/best-practice/findings/{finding_id}/accept", response_model=None)
def accept_finding(
    finding_id: uuid.UUID, db: DbSession, current_user=Depends(require_permission("best_practice.triage"))
):
    finding = service.accept_finding(db, finding_id)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="FINDING_ACCEPTED",
        object_type="architecture_finding",
        object_id=finding.id,
        result="SUCCESS",
    )
    db.commit()
    return success(_finding_out(db, finding))


@router.post("/best-practice/findings/{finding_id}/ignore", response_model=None)
def ignore_finding(
    finding_id: uuid.UUID,
    payload: IgnoreFindingRequest,
    db: DbSession,
    current_user=Depends(require_permission("best_practice.triage")),
):
    finding = service.ignore_finding(db, finding_id, payload.reason)
    record_audit_event(
        db,
        user_id=current_user.id,
        action="FINDING_IGNORED",
        object_type="architecture_finding",
        object_id=finding.id,
        result="SUCCESS",
        new_value={"reason": payload.reason},
    )
    db.commit()
    return success(_finding_out(db, finding))
