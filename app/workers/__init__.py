"""Background workers for async task processing."""

import asyncio

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import settings

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

# Global event loop for each worker process
_loop = None


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize a persistent event loop when worker process starts"""
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    """Clean up event loop when worker process shuts down"""
    global _loop
    if _loop is not None:
        _loop.close()
        _loop = None


def async_celery_task(*celery_args, **celery_kwargs):
    """Decorator that makes async functions work as Celery tasks"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            global _loop
            if _loop is None:
                # Fallback if signal didn't fire
                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)
            return _loop.run_until_complete(func(*args, **kwargs))

        # Register as Celery task
        return celery_app.task(*celery_args, **celery_kwargs)(wrapper)

    return decorator
