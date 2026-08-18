import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.domains.audit.models import AuditEvent


def _compute_hash(prev_hash: str | None, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    digest_input = f"{prev_hash or ''}|{serialized}".encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


def _last_hash(db: Session) -> str | None:
    last = db.scalar(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(1))
    return last.hash if last else None


def record_audit_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    result: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    source_ip: str | None = None,
    related_job: str | None = None,
) -> AuditEvent:
    """Appends a tamper-evident audit event (hash-chained). Caller is responsible for db.commit()."""
    timestamp = utcnow()
    prev_hash = _last_hash(db)
    payload = {
        "timestamp": timestamp.isoformat(),
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "object_type": object_type,
        "object_id": str(object_id) if object_id else None,
        "result": result,
        "old_value": old_value,
        "new_value": new_value,
    }
    event = AuditEvent(
        timestamp=timestamp,
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        old_value=old_value,
        new_value=new_value,
        event_metadata=metadata,
        source_ip=source_ip,
        related_job=related_job,
        prev_hash=prev_hash,
        hash=_compute_hash(prev_hash, payload),
    )
    db.add(event)
    db.flush()
    return event
