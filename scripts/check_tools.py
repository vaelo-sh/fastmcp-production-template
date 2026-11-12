"""Lint tool definitions against docs/tool-design.md, and guard a schema snapshot.

    uv run python scripts/check_tools.py                    # lint the app server
    uv run python scripts/check_tools.py --update-snapshot  # accept schema/description changes
    uv run python scripts/check_tools.py --server live/build/server.py:mcp

Exit code 1 on any lint error or snapshot drift. Cheap enough for every commit.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path

from fastmcp import Client, FastMCP

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "server" / "tests" / "tools.snapshot.json"
VERBS = {"search", "list", "get", "create", "update", "delete", "add", "remove", "send", "run", "check", "set"}
NAME_RE = re.compile(r"^[a-z]+(_[a-z0-9]+)+$")
MAX_WORDS = 120


def load_server(spec: str) -> FastMCP:
    """'app.server:mcp' (module) or 'path/to/file.py:mcp' (file)."""
    target, _, attr = spec.partition(":")
    attr = attr or "mcp"
    if target.endswith(".py"):
        path = (ROOT / target) if not Path(target).is_absolute() else Path(target)
        mod_spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(mod_spec)
        sys.path.insert(0, str(path.parent))
        mod_spec.loader.exec_module(module)
    else:
        module = importlib.import_module(target)
    return getattr(module, attr)


async def list_tools(server: FastMCP) -> list:
    async with Client(server) as c:
        return await c.list_tools()


def lint(tools: list) -> list[str]:
    errors: list[str] = []
    for t in tools:
        where = f"{t.name}:"
        if not NAME_RE.match(t.name) or t.name.split("_")[0] not in VERBS:
            errors.append(f"{where} name should be verb_noun snake_case with a verb from {sorted(VERBS)}")
        desc = (t.description or "").strip()
        first = desc.splitlines()[0] if desc else ""
        if not first or len(first) > 100:
            errors.append(f"{where} first description line must say what it does in <=100 chars")
        if "Use when" not in desc:
            errors.append(f"{where} description needs a 'Use when:' line")
        if "Don't use for" not in desc:
            errors.append(f"{where} description needs a \"Don't use for:\" line naming the alternative")
        if len(desc.split()) > MAX_WORDS:
            errors.append(f"{where} description is over {MAX_WORDS} words")
        props = (t.input_schema or {}).get("properties", {})
        for pname, prop in props.items():
            if not prop.get("description"):
                errors.append(f"{where} parameter '{pname}' has no description")
        ann = t.annotations
        if ann is None or ann.read_only_hint is None:
            errors.append(f"{where} set annotations.readOnlyHint explicitly")
        if t.name.split("_")[0] in {"search", "list"} and not {"limit", "cursor"} <= set(props):
            errors.append(f"{where} list/search tools need 'limit' and 'cursor' parameters")
        if ann is not None and ann.read_only_hint is False and not ann.idempotent_hint and "idempotency_key" not in props:
            errors.append(f"{where} write tools need an 'idempotency_key' parameter (or idempotentHint=true)")
        if not t.output_schema:
            errors.append(f"{where} declare a return type so the tool has an output schema")
    return errors


def snapshot_of(tools: list) -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
            "output_schema": t.output_schema,
            "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else None,
        }
        for t in tools
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="app.server:mcp")
    ap.add_argument("--update-snapshot", action="store_true")
    ap.add_argument("--no-snapshot", action="store_true", help="lint only")
    args = ap.parse_args()

    tools = asyncio.run(list_tools(load_server(args.server)))
    errors = lint(tools)
    for e in errors:
        print(f"LINT  {e}")

    drift = False
    if not args.no_snapshot and args.server == "app.server:mcp":
        current = snapshot_of(tools)
        if args.update_snapshot or not SNAPSHOT.exists():
            SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
            print(f"snapshot written: {SNAPSHOT.relative_to(ROOT)}")
        elif json.loads(SNAPSHOT.read_text()) != json.loads(json.dumps(current)):
            drift = True
            print("SNAPSHOT  tool schemas or descriptions changed. Review the diff, re-run evals, then --update-snapshot.")

    print(f"{len(tools)} tools checked, {len(errors)} lint errors{', snapshot drift' if drift else ''}")
    return 1 if errors or drift else 0


if __name__ == "__main__":
    sys.exit(main())
