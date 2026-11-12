# Build from the repo root:   docker build -f server/Dockerfile -t mcp-to-prod .
# Run:                        docker run -p 8080:8080 -e MCP_AUTH=static -e MCP_DEV_TOKEN=... mcp-to-prod

# ---- build: resolve deps from uv.lock into a venv ----
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra otel
COPY server ./server
RUN uv sync --frozen --no-dev --no-editable --extra otel

# ---- runtime: just the venv, non-root ----
FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build /src/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MCP_ENV=prod \
    MCP_TRANSPORT=http \
    MCP_LOG_FORMAT=json \
    PORT=8080
USER app
WORKDIR /app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/health', timeout=2)"
# MCP_ENV=prod refuses to start over HTTP without auth: set MCP_AUTH (static or jwt).
CMD ["sh", "-c", "exec uvicorn app.asgi:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
