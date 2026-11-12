---
id: mcp-observe
kind: skill
name: mcp-observe
description: Turn on and verify OpenTelemetry tracing and structured JSON logs for a FastMCP server, and set up starter alerts. Use when adding observability, debugging slow or failing tool calls, or preparing a server for production.
version: "2026.11"
tags: [fastmcp, observability, opentelemetry, logging, alerts]
---

# Observe an MCP server

1. Quick look, no collector needed:
   ```bash
   MCP_TRANSPORT=http MCP_OTEL_CONSOLE=1 uv run mcp-to-prod
   uv run python scripts/smoke.py http://127.0.0.1:8000/mcp
   ```
   Spans named `tools/call <tool>` go to stderr. Every `app.requests` log line has
   `trace_id`, `tool`, `outcome`, and `duration_ms`.
2. Real traces: `uv sync --extra otel`, set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`,
   or run `docker compose -f server/compose.yaml up` and open Jaeger on :16686.
3. Never log tool arguments or tokens. The request log omits arguments, and the JSON formatter
   redacts token-like fields. Keep it that way when adding fields.
4. Alerts: copy the starter rules from `docs/observability.md`. They are suggestions, so tune them
   after a week of real traffic.
