# Stage 1: Build dependencies
FROM python:3.12.8-slim@sha256:2ec5a4a5c3e919570f57675471f081d6299668d909feabd8d4803c6c61af666c AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc=4:13.2.0-7 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11@sha256:7150493291eac8e903b23b66d6de24bc4fc136063b1d8c33c0189cb8ba2c62f3 /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.12.8-slim@sha256:2ec5a4a5c3e919570f57675471f081d6299668d909feabd8d4803c6c61af666c

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Create non-root user
RUN useradd -m -u 1000 brain && chown -R brain:brain /app
USER brain

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
