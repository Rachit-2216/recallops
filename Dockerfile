FROM node:22-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=7860

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./backend/
COPY demo/ ./demo/
COPY scripts/ ./scripts/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 recallops \
    && mkdir -p /data \
    && chown -R recallops:recallops /app /data

USER recallops

EXPOSE 7860
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT','7860') + '/api/health', timeout=3)); assert data['status'] in {'ok','degraded'}"

CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && exec uvicorn recallops.main:app --app-dir backend/src --host 0.0.0.0 --port ${PORT:-7860}"]
