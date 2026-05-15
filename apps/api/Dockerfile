# syntax=docker/dockerfile:1
#
# Goldeneye FastAPI service — multi-stage build.
#
# Build context MUST be the repo root so `apps/api/` and `apps/__init__.py`
# end up at the same relative paths as in local dev. The runtime image's
# `apps.api.*` import resolution depends on the project root being on sys.path
# (apps/api/src/main.py handles the sys.path insert itself).
#
#   docker build -f apps/api/Dockerfile -t ngti-api .
#   docker run --rm -p 8000:8000 \
#     -e DATABASE_URL=postgresql+asyncpg://... \
#     -e REDIS_URL=redis://... \
#     -e CORS_ALLOWED_ORIGINS=https://app.example.com \
#     ngti-api

# ── builder ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# uv ships an official "copy-from" image that just provides the binary.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Lockfile-only copy first so dep installs cache cleanly across source edits.
COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/

# Sync the locked deps into a venv at apps/api/.venv (matches local layout).
# --no-dev skips test/lint tooling. --frozen errors if uv.lock and
# pyproject.toml have drifted.
RUN cd apps/api && uv sync --frozen --no-dev

# ── runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# tini = clean PID 1 + signal forwarding (uvicorn + alembic both depend on
# graceful SIGTERM for shutdown).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bring the venv and the source over. Source comes from the build context
# directly (not from the builder) so layer caching doesn't lose source edits.
COPY --from=builder /app/apps/api/.venv /app/apps/api/.venv
COPY apps/__init__.py /app/apps/__init__.py
COPY apps/api /app/apps/api
COPY infra/migrations /app/infra/migrations

ENV VIRTUAL_ENV=/app/apps/api/.venv \
    PATH="/app/apps/api/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Railway / Fly inject $PORT at runtime; default to 8000 for plain docker run.
ENV PORT=8000
EXPOSE 8000

# Run migrations on container start; if they fail the platform restart-policy
# retries with backoff. `exec` so uvicorn replaces the shell as PID-after-tini.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "cd /app/apps/api && alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys,os; urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/v1/health',timeout=3); sys.exit(0)" || exit 1
