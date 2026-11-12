# AGENTS.md

Instructions for coding agents (Claude Code, Cursor, others) working in this repo.

## Map
- `server/app/`: FastMCP app. `server.py` (wiring), `settings.py` (env), `auth.py`, `middleware.py`, `logging_setup.py`, `telemetry.py`, `errors.py`, `tools/` (one module per domain).
- `server/tests/`: pytest with the in-memory `Client`. `tools.snapshot.json` is the tool schema snapshot.
- `evals/`: golden prompts (`cases/*.yaml`) and `run.py`.
- `skills/`, `prompts/`: Markdown with YAML frontmatter (schema: `scripts/artifact.schema.json`).
- `scripts/`: `check_tools.py` (lint and snapshot), `smoke.py`, `build_manifest.py`.
- `live/`: stream build slice. Don't edit `live/finished/` unless asked.

## Commands
```bash
uv sync
uv run pytest -q
uv run python scripts/check_tools.py
uv run python evals/run.py --mode offline
uv run python scripts/build_manifest.py
MCP_TRANSPORT=http uv run mcp-to-prod
```

## Rules
- Every new or changed tool needs a test, a golden eval case, and a reviewed snapshot update (`skills/mcp-add-tool`).
- Follow `docs/tool-design.md`: `verb_noun`, `Use when` / `Don't use for`, bounded params, `tool_error(code, message, hint)`.
- Never put secrets in code, tests, or logs. Config comes from env (`.env.example`).
- Logs go to stderr (stdout is the MCP protocol on stdio).
- Don't log tool arguments.
- After editing `skills/` or `prompts/`, run `scripts/build_manifest.py` and commit `manifest.json`.
- Pins: `fastmcp>=4.1.8,<4.2`. Bump only through the monthly changelog process.
