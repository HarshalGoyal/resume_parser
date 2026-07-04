"""HTTP middleware: API-key auth, request IDs + access logging, metrics.

Kept as plain Starlette middleware functions - no framework beyond what
FastAPI already ships.
"""

import hmac
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

from app.core.config import settings
from app.core.logging import AppLogger

logger = AppLogger("HTTP")

# Paths reachable without an API key: liveness probes and API docs.
AUTH_EXEMPT_PATHS = {"/", "/health/", "/docs", "/redoc", "/openapi.json"}

REQUEST_COUNT = Counter(
    "http_requests_total",
    "HTTP requests processed",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)


async def api_key_middleware(request: Request, call_next):
    """Require X-API-Key on all non-exempt endpoints when API_KEY is set.

    With API_KEY unset (the default), auth is disabled - local development
    works out of the box.
    """
    if settings.api_key and request.url.path not in AUTH_EXEMPT_PATHS:
        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided, settings.api_key):
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "AUTH_001",
                    "message": "Missing or invalid API key (X-API-Key header).",
                    "details": {},
                },
            )
    return await call_next(request)


async def observability_middleware(request: Request, call_next):
    """Attach a request ID, log one access line, and record metrics."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    started = time.monotonic()

    response = await call_next(request)

    elapsed_ms = (time.monotonic() - started) * 1000
    # Use the matched route template (bounded label cardinality), falling back
    # to the raw path for unmatched routes (404s).
    route = request.scope.get("route")
    path_label = getattr(route, "path", request.url.path)

    REQUEST_COUNT.labels(request.method, path_label, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, path_label).observe(elapsed_ms / 1000)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        f"rid={request_id} {request.method} {request.url.path} "
        f"-> {response.status_code} in {elapsed_ms:.1f}ms"
    )
    return response
