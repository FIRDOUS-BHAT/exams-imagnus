# ============================================
# Stage 1: Builder — install dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only requirements first (layer caching — rebuilds only when deps change)
COPY requirements.txt ./

# Install dependencies into a virtual environment
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python --no-cache -r requirements.txt


# ============================================
# Stage 2: Runtime — lean production image
# ============================================
FROM python:3.12-slim AS runtime

# Install only runtime system libraries (no gcc/build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Add venv to PATH so `uvicorn` is available directly
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check — verifies the app is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/ || exit 1

EXPOSE 8000

# Switch to non-root user
USER appuser

# Run with uvicorn in production mode
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "4"]
