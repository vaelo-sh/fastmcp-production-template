# Observability and alerts

## Logs (always on)
JSON lines on **stderr** (stdout is the protocol on stdio). One `app.requests` line per request:
```json
{"level":"INFO","logger":"app.requests","msg":"request","trace_id":"2e98…","method":"tools/call","tool":"search_notes","outcome":"ok","duration_ms":2.48}
```
`outcome` is `ok`, `tool_error` (the model can fix it), or `error` (a bug). Arguments are never
logged, and token-like fields are redacted. `MCP_LOG_FORMAT=text` gives human-readable logs locally.

## Traces (opt-in)
FastMCP creates spans for every MCP operation (`tools/call search_notes`, …) using the
[MCP semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/). They're no-ops until an SDK is configured
([FastMCP telemetry](https://gofastmcp.com/docs/servers/telemetry.md)).
- Console: `MCP_OTEL_CONSOLE=1`
- OTLP: `uv sync --extra otel`, then set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`
- Local Jaeger: `docker compose -f server/compose.yaml up --build`, then open http://localhost:16686

Log lines carry `trace_id`/`span_id`, so you can jump from a log line to its trace.

## Metrics to derive (from logs or spans)
Per tool: request rate, `error` rate, `tool_error` rate, p50/p95/p99 `duration_ms`, 401 count
(from the HTTP layer), rate-limit rejections.

## Starter alerts (SUGGESTIONS, not facts; tune after a week of real traffic)
| Alert | Suggested starting threshold | Why |
|---|---|---|
| Server error rate | `outcome=error` > 1% of requests over 10 min | bugs, dependency outages |
| Tool error spike | `tool_error` > 20% for one tool over 30 min | a description or schema is confusing agents |
| Latency | p95 `duration_ms` > 1000 ms for read tools over 15 min | slow backend |
| Auth failures | 401s > 5× the trailing-day baseline over 10 min | IdP/JWKS outage, key rotation, abuse |
| Health | `/health` failing for 2 consecutive checks | instance down |
| Error budget | 99.5% success target. Page on fast burn (2% of the month's budget in 1 h) | standard SLO practice |

Start with just two pages: error rate and health. Everything else goes to a channel, not a pager.
