# Evals: does the agent pick the right tool?

Golden cases live in `evals/cases/*.yaml`:
```yaml
- id: open-by-id
  prompt: Show me the full text of note n-003.
  expected_tool: get_note          # or "none"
  expected_args: {note_id: n-003}  # subset; strings match case-insensitively by containment
  must_not_call: [search_notes]
```

```bash
uv run python evals/run.py --mode offline        # no keys, no network
ANTHROPIC_API_KEY=… EVAL_MODEL=<model id> uv run python evals/run.py --mode live
OPENAI_API_KEY=…    EVAL_MODEL=<model id> uv run python evals/run.py --mode live
```
- **Offline** is a deterministic keyword scorer over tool names and descriptions. It catches a
  description that stops saying what the tool is for. It is **not** a model eval and skips argument checks.
- **Live** sends each prompt plus the real `tools/list` to the model, then scores the first tool
  call (tool, args, forbidden tools). You pick the model id via `EVAL_MODEL`; nothing is hard-coded.
- Results go to `evals/results/latest.json`. The run exits 1 below `min_accuracy` (set per file).
- CI runs offline on every push. Live runs nightly or on demand when an API key secret and the `EVAL_MODEL` repo variable exist.
- Point it at another server: `--server path/to/server.py:mcp --cases path/to/cases.yaml`.

Write cases in user language, include one confusable prompt per tool, and include `none` cases.
