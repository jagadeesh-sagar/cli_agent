---
name: celery
description: Celery task queue setup, task definitions, scheduling, retries, and Redis broker config. Use when adding background jobs or async processing to a Django/FastAPI project.
---

# Celery

## Setup
```python
# celery_app.py  (project root or app/celery.py)
from celery import Celery

app = Celery(
    "myproject",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["tasks.email_tasks", "tasks.report_tasks"],
)

app.conf.update(
    task_serializer="json",
    result_expires=3600,          # results expire after 1 hour
    timezone="Asia/Kolkata",
    enable_utc=True,
)
```

## Task Definition
```python
from celery_app import app
from celery.utils.log import get_task_logger

log = get_task_logger(__name__)

# Basic task
@app.task
def send_email(to: str, subject: str, body: str) -> dict:
    log.info(f"Sending email to {to}")
    # ... send email ...
    return {"status": "sent", "to": to}

# Task with retry on failure
@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,       # wait 60s before retry
    autoretry_for=(Exception,),
)
def process_payment(self, order_id: int) -> str:
    try:
        result = payment_gateway.charge(order_id)
        return result
    except TemporaryError as e:
        raise self.retry(exc=e)

# Long-running task with progress
@app.task(bind=True)
def generate_report(self, report_id: int):
    total_rows = get_row_count(report_id)
    for i, row in enumerate(get_rows(report_id)):
        process_row(row)
        self.update_state(
            state="PROGRESS",
            meta={"current": i, "total": total_rows}
        )
```

## Calling Tasks
```python
# Async (fire and forget)
send_email.delay("user@example.com", "Welcome", "Hello!")

# With options
send_email.apply_async(
    args=["user@example.com", "Hi", "Body"],
    countdown=300,                # run after 5 minutes
    expires=3600,                 # discard if not run within 1 hour
)

# Synchronous (blocks — only for testing)
result = send_email.apply(args=["x@y.com", "Test", "Body"])
print(result.get())

# Check task status
from celery.result import AsyncResult
task = AsyncResult(task_id)
print(task.status)   # PENDING, STARTED, SUCCESS, FAILURE, RETRY
```

## Periodic Tasks (Celery Beat)
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    "send-daily-digest": {
        "task": "tasks.email_tasks.send_digest",
        "schedule": crontab(hour=8, minute=0),  # every day at 8am
    },
    "cleanup-old-sessions": {
        "task": "tasks.cleanup.remove_old_sessions",
        "schedule": 3600.0,    # every hour (seconds)
    },
}
```

## Django Integration
```python
# settings.py
CELERY_BROKER_URL    = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

# myproject/__init__.py
from .celery_app import app as celery_app
__all__ = ("celery_app",)
```

## Running
```bash
# Start worker
celery -A celery_app worker --loglevel=info --concurrency=4

# Start beat scheduler (for periodic tasks)
celery -A celery_app beat --loglevel=info

# Monitor tasks in terminal
celery -A celery_app events --dump

# Flower web UI
pip install flower
celery -A celery_app flower --port=5555
```

## Rules
- Tasks must be idempotent — safe to run multiple times (retries happen)
- Never pass ORM objects to tasks — pass IDs only, re-fetch inside the task
- Keep tasks small and focused — chain complex workflows with `.si()` / `.s()`
- Always set `max_retries` — never let a task retry forever
- Use `task_always_eager=True` in test settings to run tasks synchronously
