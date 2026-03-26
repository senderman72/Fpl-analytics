export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: dev stop check delete

## Start all services (Postgres, Redis, FastAPI, Celery, Astro) via Tilt
dev:
	@command -v tilt >/dev/null 2>&1 || { echo "Error: tilt is not installed. Run: curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash"; exit 1; }
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	tilt up

## Run all linters, type checks, and tests
check:
	@echo "=== Backend: ruff ==="
	cd backend && uv run ruff check .
	@echo "=== Backend: mypy ==="
	cd backend && uv run mypy app/ worker/
	@echo "=== Backend: pytest ==="
	cd backend && uv run pytest
	@echo "=== Frontend: build ==="
	cd frontend && npm run build
	@echo "=== All checks passed ==="

## Stop all services
stop:
	tilt down
	-pkill -f "uvicorn app.main" 2>/dev/null
	-pkill -f "celery.*worker" 2>/dev/null
	-pkill -f "astro dev" 2>/dev/null

## Delete everything — clean slate (next make dev rebuilds from scratch)
delete:
	-tilt down 2>/dev/null
	docker compose down -v
	rm -rf backend/.venv backend/.ruff_cache backend/.mypy_cache backend/.pytest_cache
	rm -rf frontend/node_modules frontend/dist
	@echo "Deleted all build artifacts and volumes. Run 'make dev' to rebuild from scratch."
