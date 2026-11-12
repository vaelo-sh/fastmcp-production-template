"""ASGI app for production: `uvicorn app.asgi:app --host 0.0.0.0 --port $PORT`."""

from __future__ import annotations

from .logging_setup import setup_logging
from .settings import get_settings
from .telemetry import setup_telemetry

settings = get_settings()
setup_telemetry(settings.name, console=settings.otel_console)

from .server import mcp  # noqa: E402

setup_logging(settings.log_level, settings.log_format)  # after FastMCP installs its handlers

_kwargs: dict = {"path": settings.path, "stateless_http": settings.stateless_http}
if settings.allowed_hosts:
    _kwargs.update(host_origin_protection=True, allowed_hosts=settings.allowed_hosts)

app = mcp.http_app(**_kwargs)
