---
id: write-golden-cases
kind: prompt
name: write-golden-cases
description: Draft golden eval cases (prompt, expected tool, expected args, must-not-call) for an MCP server's tools.
version: "2026.11"
tags: [evals, testing]
---

Here are the tools on an MCP server:
{{tools}}

Write 2 to 4 golden cases per tool in this YAML shape:

- id: short-kebab-id
  prompt: what a real user would type
  expected_tool: tool_name   # or "none"
  expected_args: {key: value}   # only args that must match
  must_not_call: [other_tool]   # optional

Include, for each tool, one prompt that a confusable tool could steal, and at least one
"none" case where no tool should be called. Use plain user language, not tool names.
