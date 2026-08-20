from celery import Celery
from app.config.settings import settings

celery_app =  Celery("qdrant_management")

celery_app.config_from_object({
    "broker_url": settings.celery.broker_url,
    "result_backend": settings.celery.result_backend,
    "task_serializer": settings.celery.task_serializer,
    "result_serializer": settings.celery.result_serializer,
    "result_expires": settings.celery.result_expires,
    "task_track_started": settings.celery.task_track_started,
    "worker_max_tasks_per_child": settings.celery.worker_max_tasks_per_child,
    "accept_content": ["json"],
})

import app.celery_workers.tasks.document_version