---
id: review-tool-description
kind: prompt
name: review-tool-description
description: Rewrite one MCP tool description so agents pick it for the right requests and skip it for the wrong ones.
version: "2026.11"
tags: [tools, review]
---

You are reviewing one MCP tool definition for tool-selection quality.

Tool definition (name, description, input schema):
{{tool}}

Other tools on the same server (names and first lines):
{{other_tools}}

Rewrite the description in this exact shape, under 80 words:
1. First line: what it does, in words a user would say.
2. "Use when:" the requests it should handle.
3. "Don't use for:" the closest confusable requests, naming the tool to use instead.
4. "Example:" one realistic call.

Then list any parameter missing a description or a bound. Do not change behavior.
