"""The app: one FastMCP server that mounts domain servers and adds auth + middleware.

Run it:
    uv run mcp-to-prod                       # stdio (default)
    MCP_TRANSPORT=http uv run mcp-to-prod    # Streamable HTTP on :8000/mcp
    uv run fastmcp run server/app/server.py:mcp
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .auth import build_auth
from .middleware import build_middleware
from .settings import Settings, get_settings
from .store import NoteStore
from .tools.notes import build_notes_server

INSTRUCTIONS = """\
Team notes and runbooks. Use search_notes to find notes, get_note to read one,
create_note to save a new one. Pass an idempotency_key when creating so retries are safe.
"""


def create_server(settings: Settings | None = None, store: NoteStore | None = None) -> FastMCP:
    settings = settings or get_settings()
    store = store or NoteStore()

    mcp = FastMCP(
        settings.name,
        instructions=INSTRUCTIONS,
        version=__version__,
        auth=build_auth(settings),
        middleware=build_middleware(settings),
        mask_error_details=True,  # unexpected exceptions never leak internals
    )

    write_scope = settings.write_scope if settings.auth != "none" else None
    mcp.mount(build_notes_server(store, write_scope=write_scope))

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    return mcp


mcp = create_server()
