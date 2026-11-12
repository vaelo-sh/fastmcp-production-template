"""One error shape for every tool: code, message, hint.

Errors an agent can fix (bad input, not found) are raised as ToolError, so the
model sees an actionable message and can retry. Everything else is a bug and
gets masked by ErrorHandlingMiddleware (no stack traces leak to clients).
"""

from __future__ import annotations

from fastmcp.exceptions import ToolError


def tool_error(code: str, message: str, hint: str | None = None) -> ToolError:
    text = f"[{code}] {message}"
    if hint:
        text += f" Hint: {hint}"
    return ToolError(text)
