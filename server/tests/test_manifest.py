"""skills/ and prompts/ have valid frontmatter, and manifest.json is current."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import build_manifest  # noqa: E402


def test_manifest_builds_without_errors():
    entries, errors = build_manifest.collect()
    assert errors == []
    kinds = {e["kind"] for e in entries}
    assert kinds == {"skill", "prompt"}
    assert all(len(e["sha256"]) == 64 and e["path"] and e["version"] for e in entries)


def test_committed_manifest_is_current():
    entries, _ = build_manifest.collect()
    assert build_manifest.MANIFEST.read_text() == build_manifest.render(entries), \
        "run: uv run python scripts/build_manifest.py"


def test_bad_frontmatter_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "skills" / "Bad Skill").mkdir(parents=True)
    (tmp_path / "skills" / "Bad Skill" / "SKILL.md").write_text("---\nid: x\nkind: prompt\nname: other\nversion: 2026.11\n---\nbody\n")
    (tmp_path / "prompts").mkdir()
    monkeypatch.setattr(build_manifest, "ROOT", tmp_path)
    _, errors = build_manifest.collect()
    text = "\n".join(errors)
    assert "kind must be 'skill'" in text and "folder name" in text and "description" in text and "version" in text
