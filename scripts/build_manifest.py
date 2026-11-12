"""Validate skill/prompt frontmatter and write manifest.json.

    uv run python scripts/build_manifest.py           # validate + write manifest.json
    uv run python scripts/build_manifest.py --check   # fail if manifest.json is stale (CI)

manifest.json is what a later loader upserts into the connector's database:
one row per artifact with id, kind, version, path, sha256 (and files for skills).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "scripts" / "artifact.schema.json").read_text())
MANIFEST = ROOT / "manifest.json"


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter (file must start with ---)")
    _, fm, _body = text.split("---\n", 2)
    data = yaml.safe_load(fm) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data


def sha256_files(files: list[Path], base: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f.relative_to(base).as_posix().encode() + b"\0")
        h.update(f.read_bytes() + b"\0")
    return h.hexdigest()


def collect() -> tuple[list[dict], list[str]]:
    validator = Draft202012Validator(SCHEMA)
    entries, errors = [], []
    sources = [(p, "skill") for p in sorted((ROOT / "skills").glob("*/SKILL.md"))]
    sources += [(p, "prompt") for p in sorted((ROOT / "prompts").glob("*.md"))]
    for path, kind in sources:
        rel = path.relative_to(ROOT).as_posix()
        try:
            fm = frontmatter(path)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{rel}: {e}")
            continue
        for err in validator.iter_errors(fm):
            errors.append(f"{rel}: {'/'.join(map(str, err.path)) or '(root)'}: {err.message}")
        if fm.get("kind") != kind:
            errors.append(f"{rel}: kind must be '{kind}' for files in this folder")
        if kind == "skill":
            folder = path.parent
            if fm.get("name") != folder.name:
                errors.append(f"{rel}: name must equal the folder name '{folder.name}'")
            files = [f for f in folder.rglob("*") if f.is_file()]
            entry_path, base = folder.relative_to(ROOT).as_posix(), folder
        else:
            files, entry_path, base = [path], rel, path.parent
        entry = {
            "id": fm.get("id"), "kind": kind, "name": fm.get("name"), "version": fm.get("version"),
            "description": fm.get("description"), "tags": fm.get("tags", []),
            "path": entry_path, "sha256": sha256_files(files, base),
        }
        if kind == "skill":
            entry["files"] = sorted(f.relative_to(folder).as_posix() for f in files)
        entries.append(entry)
    seen: set[tuple] = set()
    for e in entries:
        key = (e["kind"], e["id"])
        if key in seen:
            errors.append(f"duplicate {e['kind']} id: {e['id']}")
        seen.add(key)
    return entries, errors


def render(entries: list[dict]) -> str:
    return json.dumps({"schema": 1, "artifacts": entries}, indent=2, sort_keys=True) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if manifest.json is missing or stale")
    a = ap.parse_args()
    entries, errors = collect()
    for e in errors:
        print(f"ERROR  {e}")
    if errors:
        return 1
    out = render(entries)
    if a.check:
        if not MANIFEST.exists() or MANIFEST.read_text() != out:
            print("manifest.json is stale: run scripts/build_manifest.py")
            return 1
        print(f"manifest.json up to date ({len(entries)} artifacts)")
        return 0
    MANIFEST.write_text(out)
    print(f"wrote manifest.json ({len(entries)} artifacts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
