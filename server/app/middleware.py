"""Cross-cutting behavior, in order: errors -> rate limit -> request log (method, tool, outcome, duration).

First added runs first on the way in and last on the way out, so the error
handler wraps everything and sees every failure.

Not on by default: ResponseLimitingMiddleware. In FastMCP 4.1.x it removes the
output schema from every tool it limits (truncated text can't satisfy a schema).
We keep structured output and bound response size with pagination limits instead.
"""

from __future__ import annotations

import logging
import time

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

from .settings import Settings


log = logging.getLogger("app.requests")


class RequestLogMiddleware(Middleware):
    """One JSON log line per request: the fields dashboards and alerts are built on.

    Fields: method, tool (for tools/call), outcome (ok | tool_error | error), duration_ms.
    Arguments are never logged; they can hold personal data.
    """

    async def on_request(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        fields: dict = {"method": context.method}
        if context.method == "tools/call":
            fields["tool"] = getattr(context.message, "name", None)
        try:
            result = await call_next(context)
            is_error = bool(getattr(result, "is_error", False) or getattr(result, "isError", False))
            fields["outcome"] = "tool_error" if is_error else "ok"
            return result
        except ToolError:
            fields["outcome"] = "tool_error"
            raise
        except Exception as exc:
            fields["outcome"] = "error"
            fields["error_type"] = type(exc).__name__
            raise
        finally:
            fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            level = logging.ERROR if fields.get("outcome") == "error" else logging.INFO
            log.log(level, "request", extra={"fields": fields})


def build_middleware(settings: Settings) -> list[Middleware]:
    return [
        # transform_errors=False: a ToolError must reach the client as a tool result
        # with isError=true (the model can read and fix it), not a protocol error.
        # Unexpected exceptions are still masked by FastMCP(mask_error_details=True).
        ErrorHandlingMiddleware(include_traceback=False, transform_errors=False),
        RateLimitingMiddleware(max_requests_per_second=settings.rate_limit_rps),
        RequestLogMiddleware(),
    ]
