"""File entrypoint for `fastmcp run` (which loads files, not packages).

    cd server && uv run fastmcp run          # uses fastmcp.json in this folder
"""

from app.server import mcp  # noqa: F401
