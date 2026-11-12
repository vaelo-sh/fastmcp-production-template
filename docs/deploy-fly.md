Tested. This is what Vaelo runs on.

# Deploy to Fly.io

Cloud Run is an untested alternative: [deploy-cloud-run.md](deploy-cloud-run.md).

`server/Dockerfile` is the image. Build it from the repo root. The process binds `0.0.0.0:$PORT`, and the image sets `PORT=8080` (`EXPOSE 8080`). `GET /health` needs no auth. The image sets `MCP_LOG_FORMAT=json`, `MCP_TRANSPORT=http`, and `MCP_ENV=prod`. With `MCP_ENV=prod`, the process exits until `MCP_AUTH` is `static` or `jwt`.

## 1. fly launch

From the repo root:

```bash
fly launch --no-deploy --dockerfile server/Dockerfile --internal-port 8080 --ha=false
```

`--no-deploy` writes `fly.toml` so you can set the check and the auth env before the first release. `--internal-port 8080` matches the port uvicorn binds from `PORT`. The Docker build context stays the repo root, which is what `server/Dockerfile` expects (`COPY pyproject.toml`, `COPY server`).

## 2. fly.toml

`min_machines_running` is honored when `auto_stop_machines` is `"stop"` or `"suspend"`. `1` keeps a machine up in the primary region, so the first tool call hits a warm process.

```toml
app = "mcp-to-prod"
primary_region = "iad"   # fly launch sets this

[build]
  dockerfile = "server/Dockerfile"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    grace_period = "10s"
    interval = "30s"
    method = "GET"
    timeout = "5s"
    path = "/health"
```

The check requests `/health` and expects a 2xx. That route returns `{"status":"ok"}` with no bearer token. The image's own healthcheck probes the same path.

If you change `internal_port`, set `PORT` in `[env]` to that same number. The process listens on `$PORT` from the image (8080).

## 3. Secrets

`fly secrets` holds production auth settings. They are applied as env on the machine, and they are not baked into the image or committed.

`MCP_AUTH`, `MCP_JWT_JWKS_URI`, `MCP_JWT_ISSUER`, `MCP_JWT_AUDIENCE`, and `MCP_JWT_ALGORITHM` are plain config and can live under `[env]`. Put `MCP_DEV_TOKEN` and `MCP_JWT_PUBLIC_KEY` in `fly secrets`.

Static token (`MCP_DEV_TOKEN` must be at least 16 characters):

```bash
fly secrets set \
  MCP_AUTH=static \
  MCP_DEV_TOKEN="$(openssl rand -hex 32)"
```

JWT. These are the variables `docs/auth.md` and `server/app/settings.py` read:

```bash
fly secrets set \
  MCP_AUTH=jwt \
  MCP_JWT_JWKS_URI="https://<project>.supabase.co/auth/v1/.well-known/jwks.json" \
  MCP_JWT_ISSUER="https://<project>.supabase.co/auth/v1" \
  MCP_JWT_AUDIENCE=authenticated \
  MCP_JWT_ALGORITHM=ES256
```

`MCP_AUTH=jwt` needs `MCP_JWT_JWKS_URI` or `MCP_JWT_PUBLIC_KEY` (a PEM). To publish Protected Resource Metadata, set both `MCP_AUTH_SERVERS` and `MCP_BASE_URL`. Optional: `MCP_REQUIRED_SCOPES`, `MCP_WRITE_SCOPE` (default `notes:write`).

After the hostname exists, lock Host/Origin checks to it:

```bash
fly secrets set MCP_ALLOWED_HOSTS="<app>.fly.dev"
```

## 4. Release

```bash
fly deploy
```

`fly secrets set` rolls a new release when the app already has machines. Run `fly deploy` for the first image, and again after you edit `fly.toml`.

## 5. JSON logs

The image sets `MCP_LOG_FORMAT=json`. The process writes one JSON object per line to stderr, with `trace_id` when a span is active, and redacts token-like fields. `fly logs` shows those lines.

Traces are optional. Set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`. The image is built with the `otel` extra.

## 6. Custom domain

```bash
fly certs add mcp.example.com
```

Add the A/AAAA or CNAME records the command prints, then `fly certs check mcp.example.com`. The certificate hostname is the public origin, including for OAuth:

```bash
fly secrets set \
  MCP_BASE_URL="https://mcp.example.com" \
  MCP_ALLOWED_HOSTS="mcp.example.com,<app>.fly.dev"
```

## 7. MCP client

```bash
curl -fsS "https://<app>.fly.dev/health"
uv run python scripts/smoke.py "https://<app>.fly.dev/mcp" --token "$MCP_DEV_TOKEN"
```

`scripts/smoke.py` connects as an MCP client, lists tools, and calls `search_notes`. Point Cursor or Claude Code at `https://<app>.fly.dev/mcp` the same way as [connect.md](connect.md). `MCP_AUTH=static` sends `Authorization: Bearer <MCP_DEV_TOKEN>`. `MCP_AUTH=jwt` sends the identity provider's access token. On a custom domain, use `https://mcp.example.com/mcp`.
