"""A tiny in-memory notes store so the example runs with zero infrastructure.

Swap this for your real backend (Postgres, an internal API, ...). Keep the same
shape: pure functions the tools call, no MCP types in here.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Note:
    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


SEED = [
    ("Rotating API keys", "Create the new key, deploy it, verify traffic, then revoke the old key.", ["security", "runbook"]),
    ("Postgres connection pooling", "Behind a transaction pooler (pgBouncer), disable prepared statements, require SSL, and set explicit connect/statement timeouts.", ["database", "runbook"]),
    ("Incident: elevated 5xx", "Check the error-rate dashboard, recent deploys, then upstream dependencies. Roll back first, debug second.", ["incident", "runbook"]),
    ("On-call handoff", "Handoff happens Monday 10:00. Share open incidents, noisy alerts, and pending follow-ups.", ["oncall"]),
    ("Release checklist", "Tests green, evals green, changelog written, tag the release, announce it.", ["release"]),
    ("Incident: auth failures spike", "Check the identity provider status page and the JWKS endpoint. Clock skew causes 'token not yet valid'.", ["incident", "security"]),
    ("Local dev setup", "uv sync, copy .env.example to .env, uv run pytest.", ["dev"]),
    ("Cache invalidation", "Prefer short TTLs plus explicit busting on write over clever invalidation.", ["architecture"]),
]


class NoteStore:
    def __init__(self, seed: bool = True) -> None:
        self._lock = threading.Lock()
        self._notes: dict[str, Note] = {}
        self._idempotency: dict[str, str] = {}
        self._ids = itertools.count(1)
        if seed:
            for title, body, tags in SEED:
                self._add(title, body, tags)

    def _add(self, title: str, body: str, tags: list[str]) -> Note:
        note = Note(id=f"n-{next(self._ids):03d}", title=title, body=body, tags=sorted(set(tags)))
        self._notes[note.id] = note
        return note

    def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    def search(self, query: str = "", tag: str | None = None) -> list[Note]:
        words = [w for w in query.lower().split() if w]
        hits = []
        for note in self._notes.values():
            if tag and tag not in note.tags:
                continue
            text = f"{note.title} {note.body} {' '.join(note.tags)}".lower()
            if all(w in text for w in words):
                hits.append(note)
        return sorted(hits, key=lambda n: n.id)

    def create(self, title: str, body: str, tags: list[str], idempotency_key: str | None) -> tuple[Note, bool]:
        """Returns (note, created). A repeated idempotency key returns the first note."""
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                return self._notes[self._idempotency[idempotency_key]], False
            note = self._add(title, body, tags)
            if idempotency_key:
                self._idempotency[idempotency_key] = note.id
            return note, True
