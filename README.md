# FastMCP production template
the living FastMCP kit for shipping production MCP servers

Want an expert in your agent while you build? → [vaelo.sh/connector](https://vaelo.sh/connector)

```
fastmcp-production-template/
├── server/      FastMCP production template (example: 3 notes tools)
├── skills/      agent skills for Cursor + Claude Code
├── prompts/     reusable prompts
├── evals/       golden prompts: does the agent pick the right tool?
├── docs/        auth, tool design, observability, deploy
├── live/        build-it-live slice (start → finished)
└── scripts/     tool lint, smoke test, manifest
```

## Quickstart
```bash
uv sync
uv run pytest -q
uv run python scripts/smoke.py stdio
```
That installs everything, runs the tests, and starts the server over stdio and calls its tools.

**Over HTTP:** `MCP_TRANSPORT=http uv run mcp-to-prod`, then
`uv run python scripts/smoke.py http://127.0.0.1:8000/mcp`.

## What's inside
- **Template** (`server/app/`): FastMCP 4.1.x, stdio and Streamable HTTP, env config, Dockerfile, `/health`, rate limits, masked errors.
- **Auth** (`MCP_AUTH=none|static|jwt`): JWT via JWKS (Supabase, Auth0, Clerk…), plus Protected Resource Metadata. See [docs/auth.md](docs/auth.md).
- **Tool design** rules plus a linter and schema snapshot. See [docs/tool-design.md](docs/tool-design.md).
- **Evals**: offline without keys, live with a key. See [docs/evals.md](docs/evals.md).
- **Observability**: JSON logs with trace IDs, OpenTelemetry spans, starter alerts. See [docs/observability.md](docs/observability.md).
- **Deploy**: [docs/deploy-fly.md](docs/deploy-fly.md) (default). [Cloud Run](docs/deploy-cloud-run.md) is an untested alternative.
- **Clients**: [docs/connect.md](docs/connect.md).

Make it yours: rename `server/app/tools/notes.py`, keep the rules, and run `scripts/check_tools.py`.

Targets: FastMCP 4.1.8 (`>=4.1.8,<4.2`), MCP spec 2026-07-28, Python 3.11+. Updated monthly, see [CHANGELOG.md](CHANGELOG.md).
