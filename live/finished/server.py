"""Live build, finished: one well-designed tool. Reference for the stream."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("live-notes")

NOTES = {
    "n-001": ("Rotating API keys", ["security", "runbook"]),
    "n-002": ("Postgres connection pooling", ["database", "runbook"]),
    "n-003": ("Incident: elevated 5xx", ["incident", "runbook"]),
}


class Hit(BaseModel):
    id: str
    title: str
    tags: list[str]


class SearchResult(BaseModel):
    items: list[Hit]
    next_cursor: str | None = None


@mcp.tool(annotations={"title": "Search notes", "readOnlyHint": True})
def search_notes(
    query: Annotated[str, Field(description="Keywords to match in the title or tags.")] = "",
    limit: Annotated[int, Field(description="Max results per page.", ge=1, le=50)] = 10,
    cursor: Annotated[str | None, Field(description="next_cursor from a previous page.")] = None,
) -> SearchResult:
    """Search team notes by keyword or tag.

    Use when: the user wants to find or list notes about a topic.
    Don't use for: anything that isn't about notes.
    """
    start = int(cursor or 0)
    words = query.lower().split()
    hits = [Hit(id=i, title=t, tags=g) for i, (t, g) in NOTES.items()
            if all(w in f"{t} {' '.join(g)}".lower() for w in words)]
    page = hits[start : start + limit]
    more = start + limit < len(hits)
    return SearchResult(items=page, next_cursor=str(start + limit) if more else None)


if __name__ == "__main__":
    mcp.run()
