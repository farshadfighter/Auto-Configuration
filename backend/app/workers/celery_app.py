from celery import Celery

from app.core.config import get_settings

# A standalone `celery worker` process only imports what `include=[...]` below pulls in, which
# is far narrower than the API process's import graph. Any task touching the ORM needs every
# domain's models registered first, or cross-domain foreign keys (e.g. discovery_jobs ->
# credential_profiles) fail to resolve at mapper-configuration time. Import unconditionally so
# this holds regardless of which task modules get added to `include`.
import app.db.models_registry  # noqa: F401

settings = get_settings()

# `include` makes a standalone `celery -A app.workers.celery_app worker` process import every
# task module so tasks register even though nothing else in that process imports them (the API
# process only imports task modules incidentally, via its routers).
celery_app = Celery(
    "ngfabric",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks.discovery", "app.workers.tasks.deployment"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
)
