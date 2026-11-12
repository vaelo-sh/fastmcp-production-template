"""Auth over real HTTP: none, static dev token, JWT (keys generated locally)."""

import httpx2 as httpx
import pytest
from fastmcp import Client
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from fastmcp.utilities.tests import run_server_async

from app.server import create_server
from conftest import make_settings

TOKEN = "dev-token-for-tests-0123456789"
ISSUER = "https://issuer.example.com"
AUDIENCE = "mcp-to-prod"


@pytest.fixture(scope="module")
def keys() -> RSAKeyPair:
    return RSAKeyPair.generate()


async def test_static_token(tmp_path):
    server = create_server(make_settings(auth="static", dev_token=TOKEN))
    async with run_server_async(server) as url:
        async with httpx.AsyncClient() as raw:
            r = await raw.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert r.status_code == 401
        async with Client(url, auth=TOKEN) as c:
            assert len(await c.list_tools()) == 3
            r = await c.call_tool("create_note", {"title": "t", "body": "b"})
            assert r.structured_content["created"]


def jwt_server(keys, **extra):
    return create_server(make_settings(
        auth="jwt", jwt_public_key=keys.public_key, jwt_issuer=ISSUER,
        jwt_audience=AUDIENCE, jwt_algorithm="RS256", **extra,
    ))


async def test_jwt_scopes(keys):
    reader = keys.create_token(issuer=ISSUER, audience=AUDIENCE, scopes=["notes:read"])
    writer = keys.create_token(issuer=ISSUER, audience=AUDIENCE, scopes=["notes:write"])
    async with run_server_async(jwt_server(keys)) as url:
        async with Client(url, auth=reader) as c:
            assert (await c.call_tool("search_notes", {})).structured_content["total"] == 8
            names = [t.name for t in await c.list_tools()]
            assert "create_note" not in names  # hidden without notes:write
        async with Client(url, auth=writer) as c:
            r = await c.call_tool("create_note", {"title": "t", "body": "b"})
            assert r.structured_content["created"]


async def test_jwt_wrong_audience_rejected(keys):
    token = keys.create_token(issuer=ISSUER, audience="someone-else", scopes=["notes:write"])
    async with run_server_async(jwt_server(keys)) as url:
        async with httpx.AsyncClient() as raw:
            r = await raw.post(url, headers={"Authorization": f"Bearer {token}"},
                               json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert r.status_code == 401


async def test_protected_resource_metadata_published(keys):
    server = jwt_server(keys, auth_servers=[ISSUER], base_url="http://127.0.0.1")
    async with run_server_async(server) as url:
        base = url.rsplit("/mcp", 1)[0]
        async with httpx.AsyncClient() as raw:
            r = await raw.get(f"{base}/.well-known/oauth-protected-resource/mcp")
            assert r.status_code == 200
            assert ISSUER.rstrip("/") in str(r.json()["authorization_servers"])
            unauth = await raw.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert "resource_metadata" in unauth.headers.get("www-authenticate", "")


async def test_health_route():
    async with run_server_async(create_server(make_settings())) as url:
        base = url.rsplit("/mcp", 1)[0]
        async with httpx.AsyncClient() as raw:
            r = await raw.get(f"{base}/health")
            assert r.status_code == 200 and r.json()["status"] == "ok"
