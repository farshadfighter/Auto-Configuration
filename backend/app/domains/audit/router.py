import uuid

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.domains.audit.models import AuditEvent

router = APIRouter()


@router.get("/audit/events", response_model=None)
def list_audit_events(
    db: DbSession,
    page: int = 1,
    page_size: int = 50,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    current_user=Depends(require_permission("audit.view")),
):
    query = db.query(AuditEvent)
    if object_type:
        query = query.filter(AuditEvent.object_type == object_type)
    if object_id:
        query = query.filter(AuditEvent.object_id == object_id)
    total = query.count()
    items = (
        query.order_by(AuditEvent.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = [
        {
            "id": str(e.id),
            "timestamp": e.timestamp.isoformat(),
            "user_id": str(e.user_id) if e.user_id else None,
            "action": e.action,
            "object_type": e.object_type,
            "object_id": str(e.object_id) if e.object_id else None,
            "result": e.result,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "related_job": e.related_job,
        }
        for e in items
    ]
    return success(data, meta={"page": page, "page_size": page_size, "total": total})
