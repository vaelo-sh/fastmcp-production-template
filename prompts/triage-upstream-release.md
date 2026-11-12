---
id: triage-upstream-release
kind: prompt
name: triage-upstream-release
description: Sort a FastMCP or MCP spec release into breaks-us, new-capability, or ignore for the monthly changelog.
version: "2026.11"
tags: [changelog, maintenance]
---

Release notes:
{{release_notes}}

Our pins and features in use:
{{pins_and_features}}

For each change, classify it as exactly one of:
- breaks-us: we must change code or docs (say where)
- new-capability: worth adopting (say what it would replace or enable)
- ignore: no effect on us

Return a table (change, class, action), then a 3-line summary for CHANGELOG.md
under "Upstream changes". Link the source for every row. Do not guess at
behavior the notes don't state; mark it "verify".
