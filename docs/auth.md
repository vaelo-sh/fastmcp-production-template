# Auth

One switch: `MCP_AUTH = none | static | jwt`. All config comes from env (see `.env.example`).
Code: `server/app/auth.py`. Tests: `server/tests/test_auth.py` (real HTTP, locally generated keys).

## What the spec asks (MCP 2026-07-28)
- Auth is optional. HTTP servers that use it SHOULD follow the spec's OAuth 2.1 profile.
  **stdio servers SHOULD NOT** and read credentials from the environment instead.
- A protected server is an OAuth resource server. It MUST publish **Protected Resource Metadata**
  (RFC 9728) and point to it from `WWW-Authenticate`.
- Tokens must be issued **for this server** (audience check). Token passthrough is forbidden.
- Source: [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/index.md),
  [Security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations.md).

## Modes (v1)
| `MCP_AUTH` | Use for | Set |
|---|---|---|
| `none` | stdio, local HTTP dev | nothing. `MCP_ENV=prod` refuses HTTP without auth |
| `static` | internal tools, demos, CI | `MCP_DEV_TOKEN` (≥16 chars, random). Grants all scopes |
| `jwt` | real users | `MCP_JWT_JWKS_URI` (or `MCP_JWT_PUBLIC_KEY`), `MCP_JWT_ISSUER`, `MCP_JWT_AUDIENCE`, `MCP_JWT_ALGORITHM` |

Add `MCP_AUTH_SERVERS` + `MCP_BASE_URL` to `jwt` and the server publishes
`/.well-known/oauth-protected-resource/<path>` and sends the `resource_metadata` challenge, so
OAuth-capable MCP clients can discover where to log in.

**Scopes:** `create_note` requires `MCP_WRITE_SCOPE` (default `notes:write`) when auth is on.
Tools a token can't call are hidden from `tools/list`. `MCP_REQUIRED_SCOPES` applies to every request.

## Example: Supabase JWTs via JWKS
A pattern that has worked in production: clients send their Supabase access token as
`Authorization: Bearer …`, and the server verifies it against the project's JWKS.
```bash
MCP_AUTH=jwt
MCP_JWT_JWKS_URI=https://<project>.supabase.co/auth/v1/.well-known/jwks.json
MCP_JWT_ISSUER=https://<project>.supabase.co/auth/v1
MCP_JWT_AUDIENCE=authenticated
MCP_JWT_ALGORITHM=ES256      # or RS256, matching your project's signing key
```
JWKS verification needs asymmetric signing keys. Check your project's JWT settings. Projects on
a legacy shared secret can't be verified via JWKS. FastMCP also ships a `SupabaseProvider`
(see [FastMCP Supabase](https://gofastmcp.com/docs/integrations/supabase.md)). It's not wired here.

**Entitlement (if your server is paid):** resolve user and entitlement in **one** dependency used by
every tool. The billing webhook is the source of truth. Entitle only active states (for Stripe
subscriptions: `trialing`, `active`) and deny everything else. Never unlock client-side.

## Secrets
- Env only. `.env` is git-ignored, and `.env.example` has no values.
- Prod: `fly secrets` is the default production secret store. Cloud Run Secret Manager (`--set-secrets`) is an untested alternative.
- Logs never contain tokens. The JSON formatter redacts token-like fields, and the request log omits arguments.
- Rotate `MCP_DEV_TOKEN` by deploying the new value, then revoking the old one in clients.

## Later (FastMCP supports these, not wired in v1)
OAuth Proxy / OIDC Proxy for providers without dynamic registration (GitHub, Google, Entra),
Remote OAuth with AuthKit/Descope/Auth0, client-credentials (machine-to-machine), multi-auth,
identity assertion (beta). See [FastMCP auth](https://gofastmcp.com/docs/servers/auth/authentication.md).
