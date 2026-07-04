"""Runtime LLM provider management: inspect providers, activate one via POST.

Activation is process-wide (all requests) and process-lifetime (resets to the
LLM_PROVIDER environment default on restart).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.llm import registry
from app.core.exceptions import InvalidInputError
from app.core.logging import AppLogger

router = APIRouter(prefix="/llm", tags=["LLM configuration"])

logger = AppLogger("LLMConfig")


class ProviderStatus(BaseModel):
    name: str
    active: bool
    api_key_configured: bool
    package_installed: bool
    install_hint: str | None = None
    default_model: str
    active_model: str | None = None


class ProvidersResponse(BaseModel):
    active_provider: str | None
    providers: list[ProviderStatus]


class ActivateRequest(BaseModel):
    provider: str = Field(
        description="anthropic | openai | google/gemini | bedrock/aws | fake"
    )
    model: str = Field(
        default="", description="Optional model override (blank = provider default)"
    )


class ActivateResponse(BaseModel):
    message: str
    provider: str
    model: str


def _status(name: str) -> ProviderStatus:
    info = registry.PROVIDERS[name]
    active = registry.get_active()
    is_active = active.provider == name
    installed = registry.package_installed(info)
    return ProviderStatus(
        name=name,
        active=is_active,
        api_key_configured=(not info.needs_api_key)
        or bool(registry.resolve_api_key(name)),
        package_installed=installed,
        install_hint=None if installed else f"pip install {info.package}",
        default_model=info.default_model,
        active_model=(active.model or info.default_model) if is_active else None,
    )


@router.get(
    "/providers",
    response_model=ProvidersResponse,
    summary="List LLM providers with configuration status",
)
async def list_providers():
    active = registry.get_active()
    return ProvidersResponse(
        active_provider=active.provider or None,
        providers=[_status(name) for name in registry.PROVIDERS],
    )


@router.post(
    "/activate",
    response_model=ActivateResponse,
    summary="Activate an LLM provider for AI evaluation",
)
async def activate_provider(request: ActivateRequest):
    name = registry.canonical_name(request.provider)
    info = registry.PROVIDERS.get(name)
    if info is None:
        raise InvalidInputError(
            field="provider",
            reason=f"unknown provider '{request.provider}'",
            expected=" | ".join(registry.PROVIDERS),
        )

    if not registry.package_installed(info):
        raise InvalidInputError(
            field="provider",
            reason=(
                f"provider '{name}' requires the '{info.package}' package "
                f"(pip install {info.package})"
            ),
        )

    if info.needs_api_key and not registry.resolve_api_key(name):
        env_var = f"{name.upper()}_API_KEY"
        raise InvalidInputError(
            field="provider",
            reason=(
                f"no API key configured for '{name}'. "
                f"Set {env_var} (or LLM_API_KEY) in .env and restart."
            ),
        )

    active = registry.set_active(name, request.model)
    model = active.model or info.default_model
    logger.info(f"LLM provider activated: {name} (model={model})")
    return ActivateResponse(
        message=f"LLM provider '{name}' activated",
        provider=name,
        model=model,
    )
