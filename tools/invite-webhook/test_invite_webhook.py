import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import invite_webhook as iw  # noqa: E402

SECRET = "whsec_test_secret"


def sign(payload: bytes, t: int | None = None) -> str:
    t = t or int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def event(username="octo-cat", paid=True, type_="checkout.session.completed"):
    return json.dumps({"type": type_, "data": {"object": {
        "id": "cs_test_1", "payment_status": "paid" if paid else "unpaid",
        "custom_fields": [{"key": "githubusername", "label": {"custom": "GitHub username"}, "type": "text", "text": {"value": username}}],
    }}}).encode()


def test_signature_ok_and_tampering_rejected():
    body = event()
    iw.verify_stripe_signature(body, sign(body), SECRET)
    with pytest.raises(iw.SignatureError):
        iw.verify_stripe_signature(body + b" ", sign(body), SECRET)
    with pytest.raises(iw.SignatureError):
        iw.verify_stripe_signature(body, sign(body, t=int(time.time()) - 3600), SECRET)


async def call(body: bytes, header: str | None = None):
    sent = {}

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.start":
            sent["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            sent["body"] = json.loads(msg["body"])

    scope = {"type": "http", "method": "POST", "path": "/stripe/webhook", "headers": [(b"stripe-signature", (header or sign(body)).encode())],
             "query_string": b"", "root_path": "", "scheme": "http", "server": ("t", 80), "client": ("t", 1), "http_version": "1.1"}
    await iw.app(scope, receive, send)
    return sent["status"], sent["body"]


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("GITHUB_REPO", "owner/mcp-to-prod")
    monkeypatch.setenv("INVITE_DRY_RUN", "1")


async def test_paid_session_invites_in_dry_run():
    status, body = await call(event("@octo-cat"))
    assert status == 200 and body == {"action": "dry_run", "repo": "owner/mcp-to-prod", "username": "octo-cat", "permission": "pull"}


async def test_bad_signature_400():
    status, _ = await call(event(), header="t=1,v1=deadbeef")
    assert status == 400


async def test_unpaid_and_other_events_ignored():
    assert (await call(event(paid=False)))[1]["ignored"] == "not paid"
    assert "ignored" in (await call(event(type_="charge.refunded")))[1]


async def test_invalid_username_needs_follow_up():
    assert (await call(event("not a user!")))[1]["action"] == "manual_follow_up"


async def test_real_call_path_uses_github_status(monkeypatch):
    monkeypatch.delenv("INVITE_DRY_RUN")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setattr(iw, "invite", lambda *a: 201)
    assert (await call(event()))[1]["action"] == "invited"
    monkeypatch.setattr(iw, "invite", lambda *a: 503)
    assert (await call(event()))[0] == 502
