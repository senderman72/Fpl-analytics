"""Celery application instance."""

import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fpl_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Enable TLS when using rediss:// (Railway, Upstash, etc.)
if settings.celery_broker_url.startswith("rediss://"):
    celery_app.conf.update(
        broker_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED},
        redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED},
    )

celery_app.autodiscover_tasks(["worker"])

# Register Beat schedule
from worker.schedule import beat_schedule  # noqa: E402

celery_app.conf.beat_schedule = beat_schedule
