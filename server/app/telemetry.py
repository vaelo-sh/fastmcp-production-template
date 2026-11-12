"""OpenTelemetry tracing (opt-in).

FastMCP emits spans for every MCP operation (e.g. "tools/call search_notes")
through the OpenTelemetry API. They are no-ops until an SDK is configured.
This configures one when:
  - OTEL_EXPORTER_OTLP_ENDPOINT is set  -> OTLP exporter (needs the `otel` extra), or
  - MCP_OTEL_CONSOLE=1                  -> print spans to stderr.
Alternatively, skip this and run under `opentelemetry-instrument`.
"""

from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)


def setup_telemetry(service_name: str, console: bool = False) -> bool:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not (endpoint or console):
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        log.warning("OpenTelemetry SDK not installed; install the `otel` extra to export traces")
        return False

    provider = TracerProvider(
        resource=Resource.create({"service.name": os.environ.get("OTEL_SERVICE_NAME", service_name)})
    )
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        except ImportError:
            log.warning("OTLP exporter not installed; install the `otel` extra")
            return False
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    if console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter(out=sys.stderr)))
    trace.set_tracer_provider(provider)
    log.info("tracing enabled", extra={"fields": {"otlp": bool(endpoint), "console": console}})
    return True
