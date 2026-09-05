"""Celery configuration for durable, fair long-running work."""

from __future__ import annotations

import os

from celery import Celery


broker_url = os.getenv("CELERY_BROKER_URL", "redis://task-redis:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

celery_app = Celery(
    "ai_conference", broker=broker_url, backend=result_backend,
    include=["backend.tasks"],
)
celery_app.conf.update(
    task_default_queue="generation",
    task_routes={
        "backend.tasks.index_document": {"queue": "indexing"},
        "backend.tasks.generate_answer": {"queue": "generation"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=int(os.getenv("TASK_HARD_TIME_LIMIT", "900")),
    task_soft_time_limit=int(os.getenv("TASK_SOFT_TIME_LIMIT", "840")),
    broker_connection_retry_on_startup=True,
    imports=("backend.tasks",),
    task_serializer="json",
    accept_content=("json",),
    result_serializer="json",
)
