import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domains.identity.models import User
from app.domains.identity.service import user_has_permission
from app.domains.notifications.models import Notification


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id, type=type, title=title, message=message, object_type=object_type, object_id=object_id
    )
    db.add(notification)
    db.flush()
    return notification


def notify_users(
    db: Session,
    user_ids: list[uuid.UUID],
    *,
    type: str,
    title: str,
    message: str,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
) -> None:
    """Creates one notification per recipient. Silently no-ops for an empty list - callers pass
    a best-effort recipient set (e.g. "whoever can approve this") that may legitimately be empty
    in a small deployment, and a missing notification is never worth failing the triggering
    action (a deployment, a drift run, an approval request) over."""
    for user_id in user_ids:
        create_notification(db, user_id=user_id, type=type, title=title, message=message, object_type=object_type, object_id=object_id)


def user_ids_with_permission(db: Session, code: str) -> list[uuid.UUID]:
    users = list(db.scalars(select(User).where(User.is_active.is_(True))))
    return [u.id for u in users if u.is_superuser or user_has_permission(u, code)]


def list_notifications(db: Session, user_id: uuid.UUID, *, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(query))


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        or 0
    )


def mark_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        raise NotFoundError("NOTIFICATION_NOT_FOUND", f"Notification {notification_id} not found")
    notification.is_read = True
    db.flush()
    return notification


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    notifications = list(db.scalars(select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))))
    for notification in notifications:
        notification.is_read = True
    db.flush()
    return len(notifications)
