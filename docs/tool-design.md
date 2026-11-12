# Tool design rules

Agents pick tools by reading names, descriptions, and schemas. These rules make the right
pick likely and the wrong pick fixable. `scripts/check_tools.py` enforces the checkable ones.

| Rule | Why | Checked |
|---|---|---|
| Name is `verb_noun` snake_case (`search_notes`, `create_ticket`) | Names are the first selection signal | ✅ |
| First description line says what it does, ≤100 chars | Many clients truncate | ✅ |
| `Use when:` in the user's words | Matches how people ask | ✅ |
| `Don't use for:` naming the alternative tool | Breaks ties between similar tools | ✅ |
| One `Example:` call | Shows argument shape | — |
| Description ≤120 words | Every tool's text costs context on every turn | ✅ |
| Every parameter has a description, plus bounds (`ge`, `le`, `max_length`, `pattern`) | Models fill args from descriptions, and bounds reject garbage early | ✅ descriptions |
| Return a Pydantic model (gives an output schema and structured content) | Clients and agents can rely on the shape | ✅ |
| Annotations set honestly: `readOnlyHint`, `destructiveHint`, `idempotentHint` | Clients use them for confirmations | ✅ readOnlyHint |
| List/search tools take `limit` (small default, hard max) + `cursor`, return `next_cursor` | Bounded responses, no context floods | ✅ |
| Write tools take `idempotency_key` | Agents retry, so retries must not duplicate | ✅ |
| Fixable failures: `raise tool_error(code, message, hint)` | Returns `isError: true` with a next step the model can act on | — |
| Unexpected exceptions stay masked (`mask_error_details=True`) | No stack traces or internals leak | — |
| Tools listed in a stable order | The 2026-07-28 spec says servers SHOULD, for client and prompt caching | ✅ snapshot |

## Error shape
```
[not_found] No note with id 'n-999'. Hint: Call search_notes to find the right id.
```
Use `code` values like `invalid_argument`, `not_found`, `conflict`, `rate_limited`, `invalid_cursor`.
Input that fails the schema is rejected by FastMCP before your code runs.

## Change control
`server/tests/tools.snapshot.json` holds every tool's name, description, schemas, and annotations.
Any change fails CI until you review it, re-run evals, and accept it:
```bash
uv run python scripts/check_tools.py --update-snapshot
```

## Template
See `server/app/tools/notes.py`: three tools that follow every rule above.
