---
id: mcp-add-tool
kind: skill
name: mcp-add-tool
description: Add a new tool to a FastMCP server the production way, as one change with the tool, a test, a golden eval case, and an updated schema snapshot. Use when asked to add, create, or expose a new MCP tool.
version: "2026.11"
tags: [fastmcp, tools, testing, evals]
---

# Add an MCP tool

Do all five steps in one change. A tool without a test and an eval case is not done.

1. **Design it first.** Read `docs/tool-design.md`. Pick a `verb_noun` name, typed params with
   `Annotated[..., Field(description=...)]`, a Pydantic return model (gives an output schema),
   and honest annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`).
2. **Write the tool** in the right module under `server/app/tools/` (or a new module mounted in
   `server/app/server.py`). Description: first line says what it does, then `Use when:`,
   `Don't use for:` (name the alternative tool), and one `Example:`.
   Fixable failures: `raise tool_error("code", "message", "hint")` from `app.errors`.
   List/search tools take `limit` + `cursor`. Write tools take `idempotency_key`.
3. **Test it** in `server/tests/` with the in-memory client (`client` fixture in `conftest.py`):
   happy path, one validation failure, one fixable error (`raise_on_error=False`, assert `is_error`).
4. **Add golden prompts** to `evals/cases/*.yaml`: at least one prompt that should pick the tool,
   and one confusable prompt that should pick a different tool (or `none`).
5. **Check and snapshot:**
   ```bash
   uv run pytest -q
   uv run python scripts/check_tools.py            # lint; will report snapshot drift
   uv run python evals/run.py --mode offline
   uv run python scripts/check_tools.py --update-snapshot   # only after reviewing the diff
   ```

Done when all four commands pass and the snapshot diff shows only the intended change.
