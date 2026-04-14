#!/bin/bash
set -e

# Delete .env if it got copied into the container — Railway sets env vars directly
rm -f .env

# Debug: print connection targets (host only, secrets masked)
echo "DATABASE_URL=${DATABASE_URL:-(NOT SET)}" | sed 's/:\/\/[^@]*@/:\/\/***@/'
echo "REDIS_URL=${REDIS_URL:-(NOT SET)}" | sed 's/:\/\/[^@]*@/:\/\/***@/'
echo "CELERY_BROKER_URL=${CELERY_BROKER_URL:-(NOT SET — will fall back to REDIS_URL)}" | sed 's/:\/\/[^@]*@/:\/\/***@/'

# Run Alembic migrations on startup
uv run alembic upgrade head

# Start Celery worker + beat in the background
uv run celery -A worker.celery_app worker --beat --loglevel=info --concurrency=1 &

# Start FastAPI (foreground — Railway monitors this process)
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
