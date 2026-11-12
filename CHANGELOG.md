# Changelog

Date-based releases (`YYYY.MM`, plus `.N` for same-month fixes). Each release lists what changed
upstream, what we changed, and what you need to do.

## 2026.11 (first release)

**Tested against:** FastMCP 4.1.8 · MCP spec 2026-07-28 · Python 3.12 (supports 3.11+)

### Upstream changes
- MCP spec 2026-07-28: stateless protocol (no `initialize` handshake, no `Mcp-Session-Id`), `server/discover`,
  multi-round-trip requests replace server-initiated sampling/elicitation, tasks moved to an extension. ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog.md))
- FastMCP 4: one server negotiates both protocol eras. `ctx.sample()` / `ctx.list_roots()` removed. ([what's new](https://gofastmcp.com/docs/getting-started/whats-new.md))
- FastMCP 4.2 is in alpha (requires Python 3.11 and reworks the skills API). We stay on 4.1.x until it ships.

### What we changed
- First release: template, auth (none/static/jwt + PRM), tool lint + snapshot, evals (offline/live), logs + traces, 4 skills, 3 prompts, Fly guide (default, tested) and an untested Cloud Run guide, live-build slice.
- Not enabled by default: `ResponseLimitingMiddleware`, because in 4.1.x it drops tool output schemas.

### Action needed by you
- None (first release).
