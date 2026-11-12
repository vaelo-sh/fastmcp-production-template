"""Optional: Stripe checkout -> GitHub private-repo invite. One small Starlette app.

Flow: buyer pays through a Stripe Payment Link that has a custom text field
"GitHub username" -> Stripe sends `checkout.session.completed` -> this app
verifies the signature, checks the session is paid, reads the username, and
calls GitHub "Add a repository collaborator" (read access). No database:
Stripe's event is the source of truth, and the GitHub call is safe to repeat.

Env:
  STRIPE_WEBHOOK_SECRET   whsec_... for this endpoint
  GITHUB_TOKEN            fine-grained PAT, only this repo, "Administration: write"
  GITHUB_REPO             owner/repo
  INVITE_FIELD_KEY        custom field key (default: githubusername); a field whose
                          label mentions "github" is also accepted
  INVITE_PERMISSION       pull (default) | triage | push ...
  INVITE_DRY_RUN          1 = log what would happen, call nothing

Run locally:  uv run uvicorn invite_webhook:app --app-dir tools/invite-webhook --port 8090
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

log = logging.getLogger("invite_webhook")
TOLERANCE_SECONDS = 300
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


class SignatureError(Exception):
    pass


def verify_stripe_signature(payload: bytes, header: str, secret: str, now: float | None = None) -> None:
    """Stripe scheme: HMAC-SHA256 over f"{t}.{payload}" with the endpoint secret, sent as v1=."""
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    signatures = [v for k, v in (p.split("=", 1) for p in header.split(",") if "=" in p) if k == "v1"]
    timestamp = parts.get("t")
    if not timestamp or not signatures:
        raise SignatureError("malformed Stripe-Signature header")
    if abs((now or time.time()) - int(timestamp)) > TOLERANCE_SECONDS:
        raise SignatureError("timestamp outside tolerance")
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise SignatureError("signature mismatch")


def github_username(session: dict, key: str) -> str | None:
    for field in session.get("custom_fields") or []:
        label = ((field.get("label") or {}).get("custom") or "").lower()
        if field.get("key") == key or "github" in label:
            value = ((field.get("text") or {}).get("value") or "").strip().lstrip("@")
            return value or None
    return None


def invite(repo: str, username: str, token: str, permission: str) -> int:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/collaborators/{username}",
        data=json.dumps({"permission": permission}).encode(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mcp-to-prod-invite-webhook",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status  # 201 invitation created, 204 already a collaborator
    except urllib.error.HTTPError as e:
        return e.code


async def stripe_webhook(request: Request) -> JSONResponse:
    payload = await request.body()
    try:
        verify_stripe_signature(payload, request.headers.get("stripe-signature", ""), os.environ["STRIPE_WEBHOOK_SECRET"])
    except SignatureError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    event = json.loads(payload)
    if event.get("type") != "checkout.session.completed":
        return JSONResponse({"ignored": event.get("type")})
    session = event["data"]["object"]
    if session.get("payment_status") != "paid":
        # Delayed payment methods: handle checkout.session.async_payment_succeeded the same way.
        return JSONResponse({"ignored": "not paid"})

    username = github_username(session, os.environ.get("INVITE_FIELD_KEY", "githubusername"))
    if not username or not USERNAME_RE.match(username):
        log.warning("no valid GitHub username on session %s", session.get("id"))
        # 200 so Stripe doesn't retry forever; follow up by email instead.
        return JSONResponse({"action": "manual_follow_up", "session": session.get("id")})

    repo, permission = os.environ["GITHUB_REPO"], os.environ.get("INVITE_PERMISSION", "pull")
    if os.environ.get("INVITE_DRY_RUN") == "1":
        return JSONResponse({"action": "dry_run", "repo": repo, "username": username, "permission": permission})

    status = invite(repo, username, os.environ["GITHUB_TOKEN"], permission)
    if status in (201, 204):
        return JSONResponse({"action": "invited" if status == 201 else "already_collaborator", "username": username})
    if status == 404:
        return JSONResponse({"action": "manual_follow_up", "reason": "GitHub user not found"})
    # 5xx/429 etc.: non-2xx makes Stripe retry later.
    return JSONResponse({"error": f"github status {status}"}, status_code=502)


app = Starlette(routes=[Route("/stripe/webhook", stripe_webhook, methods=["POST"])])
