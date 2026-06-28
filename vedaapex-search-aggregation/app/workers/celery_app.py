import os
from celery import Celery

# Load Redis connection settings from environment (fallback to localhost Redis)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "media_workers", broker=REDIS_URL, backend=REDIS_URL, include=["app.workers.tasks"]
)

# Standard SaaS optimization guidelines for Celery worker instances
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # Max 30 minutes for heavy 4K video rendering
    task_acks_late=True,  # Task is acknowledged after execution finishes
    worker_prefetch_multiplier=1,  # Prevent overloading single worker
    task_queues={
        "high_priority": {"exchange": "high_priority", "routing_key": "high_priority"},
        "default": {"exchange": "default", "routing_key": "default"},
        "low_priority": {"exchange": "low_priority", "routing_key": "low_priority"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)
