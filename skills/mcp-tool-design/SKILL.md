---
id: mcp-tool-design
kind: skill
name: mcp-tool-design
description: Review MCP tool definitions for agent tool-selection quality (names, descriptions, schemas, errors, pagination, idempotency) and propose concrete fixes. Use when reviewing, renaming, or rewriting tool descriptions, or when evals show the wrong tool being picked.
version: "2026.11"
tags: [fastmcp, tools, review]
---

# Review MCP tool design

1. Run `uv run python scripts/check_tools.py --no-snapshot` and fix every lint error first.
2. For each tool, check against `docs/tool-design.md`:
   - Name is `verb_noun`, and no two tools could be confused by name alone.
   - First description line says what it does in plain words a user would say.
   - `Use when:` uses the user's vocabulary, and `Don't use for:` names the alternative tool.
   - Every parameter has a description, enums beat free strings, and bounds are set (`ge`, `le`, `max_length`).
   - Errors use `tool_error(code, message, hint)` and the hint says what to do next.
   - Reads are `readOnlyHint: true`. Writes take `idempotency_key`. Lists take `limit` + `cursor`.
3. Look at `evals/results/latest.json`. For each failing case, decide whether the description or
   the case is wrong. Fix descriptions in the user's vocabulary, not by keyword stuffing.
4. Output a short table: tool → problem → proposed change. Apply only what the user approves,
   then re-run tests, evals, and `check_tools.py --update-snapshot`.
