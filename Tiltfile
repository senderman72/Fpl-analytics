# FPL Analytics — Tilt orchestration
# Starts all services with a single `tilt up`

# Ensure uv is on PATH for all commands
os.environ['PATH'] = os.path.join(os.environ['HOME'], '.local', 'bin') + ':' + os.environ.get('PATH', '')

# --- Infrastructure (Docker Compose) ---
docker_compose('./docker-compose.yml')

# --- Backend deps ---
local_resource(
    'backend-deps',
    cmd='cd backend && uv sync --group dev --quiet',
    deps=['backend/pyproject.toml'],
    labels=['backend'],
)

# --- Database migrations ---
local_resource(
    'db-migrate',
    cmd='cd backend && uv run alembic upgrade head',
    resource_deps=['postgres', 'backend-deps'],
    labels=['backend'],
)

# --- FastAPI server ---
local_resource(
    'api',
    serve_cmd='cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000',
    resource_deps=['db-migrate'],
    deps=['backend/app'],
    links=['http://localhost:8000/health', 'http://localhost:8000/docs'],
    labels=['backend'],
)

# --- Celery worker ---
local_resource(
    'celery-worker',
    serve_cmd='cd backend && uv run celery -A worker.celery_app worker --loglevel=info',
    resource_deps=['db-migrate'],
    deps=['backend/worker'],
    labels=['backend'],
)

# --- Celery beat scheduler (dispatches periodic tasks) ---
local_resource(
    'celery-beat',
    serve_cmd='cd backend && uv run celery -A worker.celery_app beat --loglevel=info',
    resource_deps=['db-migrate'],
    deps=['backend/worker'],
    labels=['backend'],
)

# --- Frontend deps ---
local_resource(
    'frontend-deps',
    cmd='cd frontend && npm install',
    deps=['frontend/package.json'],
    labels=['frontend'],
)

# --- Astro dev server ---
local_resource(
    'frontend',
    serve_cmd='cd frontend && npm run dev',
    resource_deps=['frontend-deps', 'api'],
    links=['http://localhost:4321'],
    labels=['frontend'],
)
