# Use official lightweight Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies & uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv from astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root user
RUN groupadd -r dpyb && useradd -r -g dpyb -m -d /home/dpyb dpyb

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY pyproject.toml /app/

# Install dependencies using uv into system environment
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source code & Alembic migration files
COPY app /app/app
COPY scripts /app/scripts
COPY alembic /app/alembic
COPY alembic.ini /app/
COPY README.md /app/

# Set ownership
RUN chown -R dpyb:dpyb /app

USER dpyb

ENV PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    PORT=8000

EXPOSE $PORT

# Container healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Automatic DB migration apply on startup, then launch uvicorn
CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
