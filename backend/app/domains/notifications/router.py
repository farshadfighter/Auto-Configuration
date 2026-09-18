import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.responses import success
from app.domains.notifications import service
from app.domains.notifications.schemas import NotificationOut

router = APIRouter()


@router.get("/notifications", response_model=None)
def list_notifications(db: DbSession, current_user: CurrentUser, unread_only: bool = False, limit: int = 50):
    notifications = service.list_notifications(db, current_user.id, unread_only=unread_only, limit=limit)
    return success([NotificationOut.model_validate(n).model_dump(mode="json") for n in notifications])


@router.get("/notifications/unread-count", response_model=None)
def get_unread_count(db: DbSession, current_user: CurrentUser):
    return success({"count": service.unread_count(db, current_user.id)})


@router.post("/notifications/{notification_id}/read", response_model=None)
def mark_notification_read(notification_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    notification = service.mark_read(db, notification_id, current_user.id)
    db.commit()
    return success(NotificationOut.model_validate(notification).model_dump(mode="json"))


@router.post("/notifications/read-all", response_model=None)
def mark_all_notifications_read(db: DbSession, current_user: CurrentUser):
    count = service.mark_all_read(db, current_user.id)
    db.commit()
    return success({"marked_read": count})
