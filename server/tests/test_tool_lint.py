"""Tool definitions follow docs/tool-design.md and match the committed snapshot."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import check_tools  # noqa: E402

from app.server import create_server  # noqa: E402
from conftest import make_settings  # noqa: E402


async def tools():
    return await check_tools.list_tools(create_server(make_settings()))


async def test_tools_pass_lint():
    assert check_tools.lint(await tools()) == []


async def test_tools_match_snapshot():
    snap = json.loads(check_tools.SNAPSHOT.read_text())
    current = json.loads(json.dumps(check_tools.snapshot_of(await tools())))
    assert snap == current, "Tool schema/description changed: run check_tools.py --update-snapshot after review"


def test_lint_catches_a_bad_tool():
    from fastmcp import FastMCP
    import asyncio

    bad = FastMCP("bad")

    @bad.tool
    def notes(q: str) -> str:
        """does stuff"""
        return q

    errors = check_tools.lint(asyncio.run(check_tools.list_tools(bad)))
    assert any("verb_noun" in e for e in errors)
    assert any("Use when" in e for e in errors)
    assert any("no description" in e for e in errors)
