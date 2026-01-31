"""
Celery configuration for background task processing.

This module configures Celery for:
- Campaign execution tasks
- Asset generation
- Report generation
- Data processing
"""
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)

# Get Redis URL from environment or use default
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "marketing_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.campaign_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 minutes
    
    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute between retries
    task_max_retries=3,
    
    # Queue settings
    task_default_queue="default",
    task_routes={
        "app.tasks.campaign_tasks.*": {"queue": "campaigns"},
    },
)


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """Log task start."""
    logger.info(f"Starting task {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """Log task completion."""
    logger.info(f"Completed task {task.name}[{task_id}] with state {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """Log task failure."""
    logger.error(f"Task failed {task_id}: {exception}")


if __name__ == "__main__":
    celery_app.start()
