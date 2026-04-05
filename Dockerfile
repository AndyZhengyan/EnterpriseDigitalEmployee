# ========================
# Stage 1: Builder
# ========================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install -e ".[dev]"

# ========================
# Stage 2: Runtime
# ========================
FROM python:3.13-slim AS runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source code
COPY . .

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default: run gateway. Override with --entrypoint or CMD per service.
ENTRYPOINT ["python", "-m", "uvicorn"]
# Default port overridden by SERVICE_PORT env var in compose
CMD ["apps.gateway.main:app", "--host", "0.0.0.0", "--port", "${SERVICE_PORT:-8000}"]
