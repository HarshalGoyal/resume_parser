"""Self-describing API index.

Introspects the live application's routing table at request time and returns,
for every real API endpoint, its method/path/summary plus a ready-to-run curl
command. Introspection (rather than a hand-maintained list) keeps this in sync
as endpoints are added or removed.
"""

import inspect

from fastapi import APIRouter, Request, UploadFile
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.logging import AppLogger


router = APIRouter(prefix="/info", tags=["Info"])

logger = AppLogger("Info")

# Methods that are auto-added by the framework and carry no useful curl example.
_IGNORED_METHODS = {"HEAD", "OPTIONS"}


def _file_param_names(endpoint) -> list[str]:
    """Return names of the endpoint's parameters typed as UploadFile."""
    names: list[str] = []
    try:
        signature = inspect.signature(endpoint)
    except (TypeError, ValueError):
        return names
    for name, param in signature.parameters.items():
        annotation = param.annotation
        if annotation is UploadFile or getattr(annotation, "__name__", "") == "UploadFile":
            names.append(name)
    return names


def _curl_for(method: str, url: str, endpoint) -> str:
    """Build an illustrative curl command for a single method + endpoint."""
    if method in ("POST", "PUT", "PATCH"):
        file_params = _file_param_names(endpoint)
        if file_params:
            forms = " ".join(
                f"-F '{name}=@/path/to/resume.pdf'" for name in file_params
            )
            return f"curl -X {method} {forms} {url}"
        return (
            f"curl -X {method} -H 'Content-Type: application/json' "
            f"-d '{{}}' {url}"
        )
    if method == "GET":
        return f"curl {url}"
    return f"curl -X {method} {url}"


@router.get("")
async def list_endpoints(request: Request):
    """List every available API endpoint with a curl usage example."""
    logger.info("Listing available API endpoints")

    base_url = str(request.base_url).rstrip("/")
    endpoints = []

    for route in request.app.routes:
        if not isinstance(route, APIRoute):
            # Skips framework routes like /docs, /redoc, /openapi.json.
            continue

        # Path params are shown as <name> placeholders in the curl example.
        display_path = route.path.replace("{", "<").replace("}", ">")
        url = f"{base_url}{display_path}"

        for method in sorted(route.methods - _IGNORED_METHODS):
            endpoints.append(
                {
                    "name": route.name,
                    "method": method,
                    "path": route.path,
                    "summary": route.summary or (route.description or "").split("\n")[0],
                    "tags": route.tags or [],
                    "curl": _curl_for(method, url, route.endpoint),
                }
            )

    endpoints.sort(key=lambda e: (e["path"], e["method"]))

    return {
        "app": settings.app_name,
        "version": settings.version,
        "count": len(endpoints),
        "endpoints": endpoints,
    }
