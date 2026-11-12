"""Example domain: a team notes / runbook store.

Three tools that show the rules in docs/tool-design.md:
- search_notes: read-only, paginated (cursor + limit)
- get_note:     read-only, actionable not-found error
- create_note:  write, safe to retry with an idempotency key
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from pydantic import BaseModel, Field

from ..errors import tool_error
from ..store import Note, NoteStore

MAX_LIMIT = 50


class NoteSummary(BaseModel):
    id: str
    title: str
    tags: list[str]


class SearchResult(BaseModel):
    items: list[NoteSummary]
    next_cursor: str | None = Field(None, description="Pass back as `cursor` to get the next page. Null when done.")
    total: int


class NoteOut(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str]
    created_at: str


class CreateResult(BaseModel):
    note: NoteOut
    created: bool = Field(description="False when an earlier call with the same idempotency_key already created it.")


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _decode_cursor(cursor: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        assert raw.startswith("o:")
        return max(0, int(raw[2:]))
    except Exception:
        raise tool_error("invalid_cursor", "The cursor is not valid.", "Use next_cursor exactly as returned, or omit it to start over.")


def _out(note: Note) -> NoteOut:
    return NoteOut(**note.__dict__)


def build_notes_server(store: NoteStore, write_scope: str | None = None) -> FastMCP:
    """Build the notes tools as their own small server, to be mounted by the app."""
    notes = FastMCP("notes", mask_error_details=True)

    @notes.tool(annotations={"title": "Search notes", "readOnlyHint": True, "openWorldHint": False})
    def search_notes(
        query: Annotated[str, Field(description="Keywords to match in title, body, or tags. Empty string lists everything.", max_length=200)] = "",
        tag: Annotated[str | None, Field(description="Only return notes with this exact tag, e.g. 'incident'.")] = None,
        limit: Annotated[int, Field(description="Max results per page.", ge=1, le=MAX_LIMIT)] = 10,
        cursor: Annotated[str | None, Field(description="next_cursor from a previous page. Omit for the first page.")] = None,
    ) -> SearchResult:
        """Search or list team notes by keyword or tag. Results are ordered by id and paginated.

        Use when: the user wants to find, look up, or list notes about a topic or with a tag.
        Don't use for: reading one note's full text when you already have its id (use get_note).
        Example: search_notes(query="api keys") or search_notes(tag="incident").
        """
        hits = store.search(query=query, tag=tag)
        start = _decode_cursor(cursor) if cursor else 0
        page = hits[start : start + limit]
        end = start + len(page)
        return SearchResult(
            items=[NoteSummary(id=n.id, title=n.title, tags=n.tags) for n in page],
            next_cursor=_encode_cursor(end) if end < len(hits) else None,
            total=len(hits),
        )

    @notes.tool(annotations={"title": "Get note", "readOnlyHint": True, "openWorldHint": False})
    def get_note(
        note_id: Annotated[str, Field(description="The note id, like 'n-003'.", pattern=r"^n-\d{3,}$")],
    ) -> NoteOut:
        """Read one note's full text by its id.

        Use when: the user names a specific note id, or after search_notes to open a result.
        Don't use for: finding notes by topic (use search_notes).
        Example: get_note(note_id="n-003").
        """
        note = store.get(note_id)
        if note is None:
            raise tool_error("not_found", f"No note with id {note_id!r}.", "Call search_notes to find the right id.")
        return _out(note)

    write_auth = require_scopes(write_scope) if write_scope else None

    @notes.tool(
        annotations={"title": "Create note", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
        auth=write_auth,
    )
    def create_note(
        title: Annotated[str, Field(description="Short title, under 120 characters.", min_length=1, max_length=120)],
        body: Annotated[str, Field(description="The note text. Plain text or Markdown.", min_length=1, max_length=20_000)],
        tags: Annotated[list[str], Field(description="Lowercase tags, e.g. ['runbook', 'database'].", max_length=10)] = [],
        idempotency_key: Annotated[str | None, Field(description="Any unique string. Retrying with the same key returns the first note instead of creating a duplicate.", max_length=100)] = None,
    ) -> CreateResult:
        """Save a new note with a title, body, and optional tags.

        Use when: the user asks to save, write down, record, or add a note.
        Don't use for: editing an existing note (not supported in this example).
        Example: create_note(title="Deploy checklist", body="1. ...", tags=["release"], idempotency_key="chat-42-1").
        """
        clean_tags = [t.strip().lower() for t in tags if t.strip()]
        note, created = store.create(title.strip(), body, clean_tags, idempotency_key)
        return CreateResult(note=_out(note), created=created)

    return notes
