"""Behavior tests for the example tools, using the in-memory FastMCP client."""

import pytest


async def test_lists_three_tools_in_stable_order(client):
    names = [t.name for t in await client.list_tools()]
    assert names == ["search_notes", "get_note", "create_note"]


async def test_search_by_keyword(client):
    r = await client.call_tool("search_notes", {"query": "api keys"})
    assert [i["id"] for i in r.structured_content["items"]] == ["n-001"]


async def test_search_by_tag(client):
    r = await client.call_tool("search_notes", {"tag": "incident"})
    assert {i["id"] for i in r.structured_content["items"]} == {"n-003", "n-006"}


async def test_pagination_walks_every_note_once(client):
    seen, cursor = [], None
    while True:
        args = {"limit": 3, **({"cursor": cursor} if cursor else {})}
        page = (await client.call_tool("search_notes", args)).structured_content
        seen += [i["id"] for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == page["total"] == 8


async def test_bad_cursor_is_a_fixable_tool_error(client):
    r = await client.call_tool("search_notes", {"cursor": "nope"}, raise_on_error=False)
    assert r.is_error and "[invalid_cursor]" in r.content[0].text


async def test_limit_is_bounded(client):
    r = await client.call_tool("search_notes", {"limit": 500}, raise_on_error=False)
    assert r.is_error


async def test_get_note(client):
    r = await client.call_tool("get_note", {"note_id": "n-002"})
    assert "pgBouncer" in r.structured_content["body"]


async def test_get_missing_note_has_hint(client):
    r = await client.call_tool("get_note", {"note_id": "n-999"}, raise_on_error=False)
    assert r.is_error
    assert "[not_found]" in r.content[0].text and "search_notes" in r.content[0].text


async def test_create_is_idempotent_with_key(client, store):
    args = {"title": "Deploy checklist", "body": "1. tests", "tags": ["Release "], "idempotency_key": "k1"}
    first = (await client.call_tool("create_note", args)).structured_content
    again = (await client.call_tool("create_note", args)).structured_content
    assert first["created"] is True and again["created"] is False
    assert first["note"]["id"] == again["note"]["id"]
    assert first["note"]["tags"] == ["release"]
    assert len(store.search()) == 9


@pytest.mark.parametrize("bad", [{"title": "", "body": "x"}, {"title": "x" * 121, "body": "x"}])
async def test_create_validates_input(client, bad):
    r = await client.call_tool("create_note", bad, raise_on_error=False)
    assert r.is_error


async def test_every_tool_has_output_schema(client):
    for tool in await client.list_tools():
        assert tool.output_schema, tool.name
