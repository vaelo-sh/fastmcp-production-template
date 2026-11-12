# Build it live

Goal for one stream: **scaffold → one tool → one test → one eval**, from near-empty.
`live/start/` is the starting point, and `live/finished/` is the reference (it passes all checks).

```bash
./live/reset.sh                       # copies start/ → build/ (git-ignored)
```

| Step | Do | Check |
|---|---|---|
| 1. Scaffold | open `live/build/server.py`, explain FastMCP + transports | `uv run python live/build/server.py` (stdio, Ctrl-C) |
| 2. First tool | add `search_notes` with typed params, `limit`/`cursor`, a Pydantic return, `Use when` / `Don't use for` | `uv run python scripts/check_tools.py --server live/build/server.py:mcp` |
| 3. First test | in `live/build/test_server.py`, call it through the in-memory `Client` | `uv run pytest -q live/build` (red → green) |
| 4. First eval | add 2 cases to `live/build/golden.yaml` (one hit, one `none`) | `uv run python evals/run.py --mode offline --server live/build/server.py:mcp --cases live/build/golden.yaml` |
| 5. Over HTTP | `uv run fastmcp run live/build/server.py:mcp --transport http --port 8000` | in a second terminal: `uv run fastmcp list http://127.0.0.1:8000/mcp` |

**Clip moments:** first run boots, the lint going from errors to 0, red→green test, eval 100%.
**Stuck?** `diff -ru live/build live/finished`.
