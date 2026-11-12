"""FastMCP emits a span per MCP operation; check one arrives with the tool name."""

from fastmcp import Client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.server import create_server
from conftest import make_settings

exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(_provider)


async def test_tool_call_creates_span():
    exporter.clear()
    async with Client(create_server(make_settings())) as c:
        await c.call_tool("search_notes", {"query": "postgres"})
    names = [s.name for s in exporter.get_finished_spans()]
    assert any("tools/call" in n and "search_notes" in n for n in names), names


def test_json_logs_carry_trace_id(capsys):
    import logging

    from app.logging_setup import setup_logging

    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    setup_logging("INFO", "json")
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("demo"):
        logging.getLogger("app.test").info("hello", extra={"fields": {"tool": "x", "token": "s3cret"}})
    root.handlers[:], _ = saved[0], root.setLevel(saved[1])
    err = capsys.readouterr().err
    assert '"trace_id"' in err and '"tool": "x"' in err and "s3cret" not in err


async def test_request_log_records_tool_and_outcome(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="app.requests")
    async with Client(create_server(make_settings())) as c:
        await c.call_tool("get_note", {"note_id": "n-999"}, raise_on_error=False)
    rec = [r for r in caplog.records if getattr(r, "fields", {}).get("tool") == "get_note"][-1]
    assert rec.fields["outcome"] == "tool_error" and rec.fields["duration_ms"] >= 0
