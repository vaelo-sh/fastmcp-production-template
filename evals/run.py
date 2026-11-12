"""Golden-prompt evals for tool selection.

    uv run python evals/run.py                  # auto: live if a key + EVAL_MODEL are set, else offline
    uv run python evals/run.py --mode offline   # no network, no keys
    ANTHROPIC_API_KEY=... EVAL_MODEL=<model id> uv run python evals/run.py --mode live
    OPENAI_API_KEY=...    EVAL_MODEL=<model id> uv run python evals/run.py --mode live

Offline mode uses a deterministic keyword scorer over tool names and descriptions.
It needs no keys and catches description regressions (a tool that stops mentioning
what it's for), but it is NOT a model eval and skips argument checks.
Live mode sends each prompt plus the real tool list to a model and scores the first
tool call: right tool, required args, no forbidden tools.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_tools import list_tools, load_server  # noqa: E402

SYSTEM = "You are an assistant with tools. Call a tool only when it helps answer the user. Otherwise answer directly."
STOP = set("a an the of to for and or in on at by with our we me my i it is are be this that these those what which who can you please about as from into just".split())


@dataclass
class Result:
    id: str
    expected: str
    got: str
    tool_ok: bool
    args_ok: bool | None
    forbidden_ok: bool
    passed: bool
    detail: str = ""
    args: dict = field(default_factory=dict)


# ---------- offline scorer ----------

def _words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP or len(w) < 2:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def offline_choose(prompt: str, tools: list) -> tuple[str, dict]:
    pwords = set(_words(prompt))
    best, best_score = "none", 0.0
    for t in tools:
        lines = [ln.strip() for ln in (t.description or "").splitlines()]
        positive = " ".join(ln for ln in lines if not ln.startswith(("Don't use", "Example")))
        score = 3 * len(pwords & set(_words(t.name.replace("_", " ")))) + len(pwords & set(_words(positive)))
        for prop in (t.input_schema or {}).get("properties", {}).values():
            pat = prop.get("pattern")
            if pat and re.search(pat.strip("^$"), prompt):
                score += 3
        if score > best_score:
            best, best_score = t.name, score
    return (best if best_score >= 3 else "none"), {}


# ---------- live providers (stdlib HTTP, no SDKs) ----------

def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def live_choose(prompt: str, tools: list, model: str) -> tuple[str, dict]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        base = os.environ.get("EVAL_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        data = _post(
            f"{base}/v1/messages",
            {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
            {
                "model": model, "max_tokens": 512, "system": SYSTEM,
                "tools": [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema} for t in tools],
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        for block in data.get("content", []):
            if block.get("type") == "tool_use":
                return block["name"], block.get("input", {})
        return "none", {}
    if os.environ.get("OPENAI_API_KEY"):
        base = os.environ.get("EVAL_OPENAI_BASE_URL", "https://api.openai.com")
        data = _post(
            f"{base}/v1/chat/completions",
            {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            {
                "model": model,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                "tools": [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.input_schema}} for t in tools],
            },
        )
        calls = data["choices"][0]["message"].get("tool_calls") or []
        if calls:
            fn = calls[0]["function"]
            return fn["name"], json.loads(fn.get("arguments") or "{}")
        return "none", {}
    raise SystemExit("live mode needs ANTHROPIC_API_KEY or OPENAI_API_KEY")


def args_match(expected: dict, got: dict) -> bool:
    for key, want in expected.items():
        have = got.get(key)
        if isinstance(want, str):
            if not isinstance(have, str) or want.lower() not in have.lower():
                return False
        elif have != want:
            return False
    return True


# ---------- runner ----------

def run(cases: list[dict], tools: list, mode: str, model: str | None) -> list[Result]:
    results = []
    for case in cases:
        expected = case["expected_tool"]
        if mode == "live":
            got, args = live_choose(case["prompt"], tools, model)
        else:
            got, args = offline_choose(case["prompt"], tools)
        tool_ok = got == expected
        args_ok = None
        if mode == "live" and tool_ok and case.get("expected_args"):
            args_ok = args_match(case["expected_args"], args)
        forbidden_ok = got not in case.get("must_not_call", [])
        passed = tool_ok and forbidden_ok and args_ok is not False
        results.append(Result(case["id"], expected, got, tool_ok, args_ok, forbidden_ok, passed, args=args))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["auto", "offline", "live"], default="auto")
    ap.add_argument("--server", default="app.server:mcp")
    ap.add_argument("--cases", default="evals/cases/*.yaml")
    ap.add_argument("--min-accuracy", type=float, default=None)
    ap.add_argument("--out", default="evals/results/latest.json")
    a = ap.parse_args()

    model = os.environ.get("EVAL_MODEL")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    mode = a.mode if a.mode != "auto" else ("live" if has_key and model else "offline")
    if mode == "live" and not model:
        raise SystemExit("live mode needs EVAL_MODEL (the model id to test against)")

    cases, min_acc = [], []
    for path in sorted(glob.glob(str(ROOT / a.cases) if not Path(a.cases).is_absolute() else a.cases)):
        data = yaml.safe_load(Path(path).read_text()) or {}
        cases += data.get("cases") or []
        if "min_accuracy" in data:
            min_acc.append(float(data["min_accuracy"]))
    if not cases:
        raise SystemExit(f"no cases found for {a.cases}")
    threshold = a.min_accuracy if a.min_accuracy is not None else (min(min_acc) if min_acc else 0.9)

    tools = asyncio.run(list_tools(load_server(a.server)))
    results = run(cases, tools, mode, model)

    width = max(len(r.id) for r in results)
    for r in results:
        args = "-" if r.args_ok is None else ("ok" if r.args_ok else f"MISMATCH {r.args}")
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.id:<{width}}  expected={r.expected:<13} got={r.got:<13} args={args}")
    acc = sum(r.passed for r in results) / len(results)
    print(f"\nmode={mode}{' model=' + model if mode == 'live' else ''}  accuracy={acc:.0%}  threshold={threshold:.0%}  cases={len(results)}")

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "mode": mode, "model": model if mode == "live" else None,
                               "accuracy": acc, "threshold": threshold, "results": [asdict(r) for r in results]}, indent=2))
    return 0 if acc >= threshold else 1


if __name__ == "__main__":
    sys.exit(main())
