import pytest
from fastmcp import Client

from server import mcp


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


async def test_search_finds_postgres(client):
    r = await client.call_tool("search_notes", {"query": "postgres"})
    assert [i["id"] for i in r.structured_content["items"]] == ["n-002"]


async def test_pagination(client):
    r = await client.call_tool("search_notes", {"limit": 2})
    assert len(r.structured_content["items"]) == 2 and r.structured_content["next_cursor"] == "2"
