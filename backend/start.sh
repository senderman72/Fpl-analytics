#!/bin/bash
set -e

# Run Alembic migrations on startup
uv run alembic upgrade head

# Start Celery worker + beat in the background
uv run celery -A worker.celery_app worker --beat --loglevel=info --concurrency=1 &

# Start FastAPI (foreground — Railway monitors this process)
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
