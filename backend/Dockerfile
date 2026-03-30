FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-editable

# Copy application code
COPY app/ app/
COPY worker/ worker/
COPY alembic/ alembic/
COPY alembic.ini .
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
