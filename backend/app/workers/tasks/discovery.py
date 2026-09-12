import uuid

from app.db.session import SessionLocal
from app.domains.discovery import service as discovery_service
from app.workers.celery_app import celery_app


@celery_app.task(name="discovery.execute_job")
def execute_discovery_job_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        discovery_service.execute_discovery_job(db, uuid.UUID(job_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
