import uuid

from app.db.session import SessionLocal
from app.domains.deployment import service as deployment_service
from app.workers.celery_app import celery_app


@celery_app.task(name="deployment.execute")
def execute_deployment_task(deployment_id: str) -> None:
    db = SessionLocal()
    try:
        deployment_service.execute_deployment(db, uuid.UUID(deployment_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
