# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
#   Installs all runtime dependencies into an isolated prefix so the final
#   image can copy only the compiled wheel-tree (no pip cache, no build tools).
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install/pkg -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — test
#   Runs the full pytest suite inside a throwaway layer.
#   Cloud Build will build and stop at this target to gate the pipeline.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS test

WORKDIR /app

# Copy installed runtime packages from builder
COPY --from=builder /install/pkg /usr/local

# Install dev-only extras (pytest, pytest-cov) on top
# requirements-dev.txt references requirements.txt via `-r`, so both must be present
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy entire project
COPY . .

# PYTHONPATH so `from src.xxx` imports resolve without installing the package
ENV PYTHONPATH=/app

RUN pytest tests/ --tb=short -q


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — lint
#   Runs ruff (style/lint) and mypy (type-checking) against the src/ package.
#   Cloud Build builds --target lint to gate the pipeline; a non-zero exit
#   code (any lint or type error) fails the build before the runtime image
#   is produced.
#
#   ruff and mypy are not included in requirements.txt (production) — they are
#   installed here directly from requirements-dev.txt which is dev-only.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS lint

WORKDIR /app

# Copy installed runtime packages from builder so imports resolve correctly
COPY --from=builder /install/pkg /usr/local

# Install dev extras (ruff, mypy, types-requests) on top of runtime packages
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source and configuration
COPY src/ ./src/
COPY pyproject.toml ./

ENV PYTHONPATH=/app

# ruff: fast linting + import sorting
RUN ruff check src/

# mypy: static type checking (configured in pyproject.toml)
RUN mypy src/


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — runtime
#   Minimal production image.  Runs the Dash app via gunicorn.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create a non-root user for Cloud Run security best-practice.
# --no-create-home keeps the image lean; HOME is explicitly set to /app below
# so Gunicorn's arbiter control server can resolve the user home path without
# hitting a "Permission denied: /home/appuser" error.
RUN useradd --system --no-create-home appuser

WORKDIR /app

# Copy pre-built packages from builder (no pip, no build-tools in final image)
COPY --from=builder /install/pkg /usr/local

# Copy only application source (not tests, not dev files)
COPY src/ ./src/
COPY requirements.txt .

# Give appuser ownership of the working directory so Gunicorn workers can
# write temp files (e.g. heartbeat files) under /app.
RUN chown -R appuser:appuser /app

ENV PYTHONPATH=/app
ENV PORT=8080
# HOME must point to a directory the process can write to.
# Without this, Gunicorn's arbiter resolves HOME to /home/appuser which
# was never created (--no-create-home), causing:
#   [Errno 13] Permission denied: '/home/appuser'
ENV HOME=/app
# Emit structured JSON logs — Google Cloud Logging parses these natively so
# each log field (severity, voice_name, encoding, etc.) becomes a filterable
# attribute in Cloud Console.  Set to "text" for human-readable plain output.
ENV LOG_FORMAT=json
# WEB_CONCURRENCY controls the number of gunicorn worker processes.
# Gunicorn reads this variable natively; override at runtime (e.g. Cloud Run
# --set-env-vars or docker run -e) without rebuilding the image.
# Default (2×CPU+1 for 1 vCPU): 3
ENV WEB_CONCURRENCY=3

USER appuser

# gunicorn serves the Flask-wrapped Dash WSGI app.
# Worker count is driven by WEB_CONCURRENCY (set above or overridden at runtime).
# --threads 4 gives each sync worker 4 concurrent slots, matching the docker-compose
# configuration so local and production environments behave identically.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--threads", "4", "--timeout", "120", "--limit-request-line", "0", "src.main:server"]

EXPOSE 8080

# Lightweight liveness probe for docker ps / docker-compose health visibility.
# Cloud Run also uses the /healthz HTTP path configured at deploy time.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1
