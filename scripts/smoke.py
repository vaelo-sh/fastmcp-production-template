"""Smoke test a running server like a real client would.

    uv run python scripts/smoke.py stdio                       # spawns the server over stdio
    uv run python scripts/smoke.py http://127.0.0.1:8000/mcp   # an HTTP server you started
    uv run python scripts/smoke.py https://host/mcp --token $MCP_DEV_TOKEN
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def main(target: str, token: str | None) -> None:
    if target == "stdio":
        transport = StdioTransport(
            command=sys.executable, args=["-m", "app"],
            env={**os.environ, "MCP_TRANSPORT": "stdio", "MCP_AUTH": "none"},
        )
        client = Client(transport)
    else:
        client = Client(target, auth=token)
    async with client:
        print("protocol:", client.protocol_version)
        print("tools:", [t.name for t in await client.list_tools()])
        found = await client.call_tool("search_notes", {"query": "postgres"})
        print("search_notes:", found.structured_content)
        note = await client.call_tool("get_note", {"note_id": found.structured_content["items"][0]["id"]})
        print("get_note:", note.structured_content["title"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="'stdio' or an http(s) URL")
    ap.add_argument("--token", default=None)
    a = ap.parse_args()
    asyncio.run(main(a.target, a.token))
