"""Entry point: `uv run mcp-to-prod` or `python -m app`."""

from __future__ import annotations

from .logging_setup import setup_logging
from .settings import get_settings
from .telemetry import setup_telemetry


def main() -> None:
    settings = get_settings()
    setup_telemetry(settings.name, console=settings.otel_console)

    import fastmcp  # noqa: F401  (FastMCP installs its own log handlers on import)

    setup_logging(settings.log_level, settings.log_format)  # ...so take them over afterwards

    from .server import mcp

    if settings.transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    else:
        mcp.run(
            transport="http",
            host=settings.host,
            port=settings.port,
            path=settings.path,
            stateless_http=settings.stateless_http,
            show_banner=False,
            **({"allowed_hosts": settings.allowed_hosts, "host_origin_protection": True} if settings.allowed_hosts else {}),
        )


if __name__ == "__main__":
    main()
