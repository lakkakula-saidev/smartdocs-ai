# SmartDocs AI Backend - Production Dockerfile
# Multi-stage build with security best practices

# Stage 1: Base dependencies stage
FROM python:3.12-slim as base

# Install system dependencies and create user in single RUN to reduce layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for PDF processing
    libpoppler-cpp-dev \
    # Build tools for Python packages
    gcc \
    g++ \
    # Cleanup in same layer
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # Create non-root user for security
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies in single RUN layer
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Stage 2: Production stage
FROM python:3.12-slim as production

# Runtime stage setup (no extra system PDF libs needed; pypdf is pure Python)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from base stage
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Create necessary directories with proper permissions
RUN mkdir -p /app/backend/vectorstores \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Set proper file permissions
RUN chmod -R 755 /app \
    && chmod -R 777 /app/backend/vectorstores \
    && chmod -R 755 /app/logs

# Switch to non-root user
USER appuser

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=structured \
    VECTOR_STORE_PERSIST_DIR=/app/backend/vectorstores

# Expose the application port
EXPOSE 8000

# Health check endpoint (stdlib only to keep image minimal; avoid adding 'requests')
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/health', timeout=8); print('ok')" || exit 1

# Use Uvicorn for production with proper configuration (single worker is fine for minimal portfolio)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "--access-log"]

# (Removed separate development stage to ensure production image is final for Railway)