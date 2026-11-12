---
id: mcp-auth-setup
kind: skill
name: mcp-auth-setup
description: Choose and wire authentication for a FastMCP server using the MCP_AUTH switch (none, static dev token, or JWT via JWKS) and publish Protected Resource Metadata for OAuth. Use when securing an HTTP MCP server, connecting an identity provider such as Supabase, Auth0, Clerk or WorkOS, or debugging 401s.
version: "2026.11"
tags: [fastmcp, auth, oauth, security]
---

# Set up auth

1. Read `docs/auth.md`. Choose:
   - stdio only → `MCP_AUTH=none` (credentials come from the environment).
   - Internal or dev HTTP → `MCP_AUTH=static` + a long random `MCP_DEV_TOKEN`.
   - Real users → `MCP_AUTH=jwt` with your IdP's JWKS URL, issuer, and audience.
2. Set the env vars from `.env.example` (never commit `.env`). For OAuth clients that discover
   auth, also set `MCP_AUTH_SERVERS` and `MCP_BASE_URL`. The server then publishes
   `/.well-known/oauth-protected-resource/<path>` and a `WWW-Authenticate` challenge.
3. Scope the write tools: `create_note` requires `MCP_WRITE_SCOPE` (default `notes:write`) when auth is on.
   Tools a token can't use are hidden from `tools/list`.
4. Verify:
   ```bash
   uv run pytest -q server/tests/test_auth.py
   MCP_TRANSPORT=http MCP_AUTH=static MCP_DEV_TOKEN=... uv run mcp-to-prod
   uv run python scripts/smoke.py http://127.0.0.1:8000/mcp --token ...
   ```
5. 401 checklist: wrong audience, wrong issuer (trailing slash), clock skew, JWKS URL unreachable
   from the server, token for a different project or environment.
