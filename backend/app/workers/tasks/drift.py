import uuid

from app.db.session import SessionLocal
from app.domains.drift import service as drift_service
from app.workers.celery_app import celery_app


@celery_app.task(name="drift.analyze")
def execute_drift_run_task(run_id: str) -> None:
    db = SessionLocal()
    try:
        drift_service.execute_drift_run(db, uuid.UUID(run_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
