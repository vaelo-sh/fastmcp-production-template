# Deploy to Google Cloud Run

The one deploy guide in v1. Written, not executed: check each command against current
[Cloud Run docs](https://cloud.google.com/run/docs/deploying) before you run it.

**Why Cloud Run:** it runs `server/Dockerfile` unchanged and scales instances on its own. Under the
2026-07-28 spec there are no protocol sessions, so any instance can answer any request
(`MCP_STATELESS_HTTP=true`, the default).

## 0. Once
```bash
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories create mcp --repository-format=docker --location=<REGION>
```

## 1. Secrets
```bash
printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create mcp-dev-token --data-file=-
# JWT mode needs no secret: JWKS URL, issuer, and audience are plain config.
```

## 2. Build and push
```bash
IMAGE=<REGION>-docker.pkg.dev/<PROJECT_ID>/mcp/mcp-to-prod:2026.11
docker build -f server/Dockerfile -t $IMAGE .
docker push $IMAGE        # after: gcloud auth configure-docker <REGION>-docker.pkg.dev
```

## 3. Deploy
```bash
gcloud run deploy mcp-to-prod \
  --image=$IMAGE --region=<REGION> \
  --allow-unauthenticated \
  --set-env-vars=MCP_ENV=prod,MCP_AUTH=static,MCP_LOG_FORMAT=json \
  --set-secrets=MCP_DEV_TOKEN=mcp-dev-token:latest \
  --min-instances=1 --max-instances=5 --concurrency=80 --timeout=300
```
- `--allow-unauthenticated`: MCP clients can't present Google IAM tokens, so the **app**
  enforces auth (`MCP_ENV=prod` refuses to start without it).
- `--min-instances=1`: keeps one warm process. Long-lived processes avoid cold-start latency on
  the first tool call. Costs a little; set it to 0 for hobby use.
- After the first deploy, set `MCP_ALLOWED_HOSTS=<service>-<hash>.<region>.run.app` (and your custom domain),
  and for OAuth, `MCP_BASE_URL=https://…`. Redeploy.

## 4. Verify
```bash
URL=$(gcloud run services describe mcp-to-prod --region=<REGION> --format='value(status.url)')
curl -s $URL/health
uv run python scripts/smoke.py $URL/mcp --token "$(gcloud secrets versions access latest --secret=mcp-dev-token)"
```
Logs: Cloud Run reads JSON on stderr as structured logs. Traces: set `OTEL_EXPORTER_OTLP_ENDPOINT`
to your collector.

## If you add a database
Behind a transaction pooler (Supabase's pooler / pgBouncer): **disable prepared statements**,
**require SSL**, and **set explicit connect and statement timeouts**. Otherwise migrations can
hang silently. Keep migrations idempotent (`IF NOT EXISTS`, `DO $$ … $$` blocks).

## Alternatives (no guide in v1)
Any container host works with the same image. Fly.io, for example, runs it as a long-lived
process (`PORT` env, `/health` check).
