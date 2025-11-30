"""Background workers for async task processing."""

import asyncio

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import settings
from app.database.client import close_supabase, init_supabase

celery_app = Celery(
    "horse_race_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.pdf_processor"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)


def async_celery_task(*celery_args, **celery_kwargs):
    """Decorator that makes async functions work as Celery tasks"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))

        # Register as Celery task
        return celery_app.task(*celery_args, **celery_kwargs)(wrapper)

    return decorator


# Worker lifecycle hooks
@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize resources when worker process starts."""
    asyncio.run(init_supabase())


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    """Clean up resources when worker process shuts down."""
    asyncio.run(close_supabase())
