# Connect a client

**Claude Code** ([docs](https://code.claude.com/docs/en/mcp)):
```bash
claude mcp add --transport http mcp-to-prod http://127.0.0.1:8000/mcp            # HTTP
claude mcp add mcp-to-prod -- uv run --directory /path/to/mcp-to-prod mcp-to-prod  # stdio
```
Add `--scope project` to write a shared `.mcp.json`.

**Cursor** ([docs](https://cursor.com/docs/mcp)), in `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):
```json
{
  "mcpServers": {
    "mcp-to-prod": { "url": "http://127.0.0.1:8000/mcp" },
    "mcp-to-prod-stdio": { "command": "uv", "args": ["run", "--directory", "/path/to/mcp-to-prod", "mcp-to-prod"] }
  }
}
```
With `MCP_AUTH=static`, add a header: `"headers": {"Authorization": "Bearer <token>"}`.

**Any client from Python:** `uv run python scripts/smoke.py http://127.0.0.1:8000/mcp [--token …]`.

**Skills:** `skills/` is plain folders of `SKILL.md`. `.claude/skills` symlinks to it. Claude Code reads
`.claude/skills/`, and Cursor reads `.claude/skills/` too (along with `.cursor/skills/` and `.agents/skills/`),
so opening this repo is enough. To use them in every project, copy the folders to `~/.claude/skills/` or `~/.cursor/skills/`.
