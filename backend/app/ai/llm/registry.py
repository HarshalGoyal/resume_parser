"""Provider registry and process-wide active-provider state.

The active provider defaults to the LLM_PROVIDER environment setting and can be
switched at runtime via POST /llm/activate. Activation is process-wide and
process-lifetime: it applies to all requests and resets to the environment
default on restart (persisting the choice is a deliberate non-goal for now).
"""

import importlib.util
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    package: str  # pip package implementing it ("" = built in)
    module: str  # importable module name for install detection
    needs_api_key: bool
    default_model: str


PROVIDERS: dict[str, ProviderInfo] = {
    "anthropic": ProviderInfo(
        "anthropic", "langchain-anthropic", "langchain_anthropic", True,
        "claude-opus-4-8",
    ),
    "openai": ProviderInfo(
        "openai", "langchain-openai", "langchain_openai", True, "gpt-4o",
    ),
    "google": ProviderInfo(
        "google", "langchain-google-genai", "langchain_google_genai", True,
        "gemini-2.0-flash",
    ),
    "bedrock": ProviderInfo(
        # Bedrock authenticates via the AWS credential chain, not an API key.
        "bedrock", "langchain-aws", "langchain_aws", False,
        "anthropic.claude-opus-4-8",
    ),
    "fake": ProviderInfo("fake", "", "", False, "fake-llm"),
}

# Accepted aliases -> canonical provider name.
ALIASES = {"gemini": "google", "aws": "bedrock"}


def canonical_name(name: str) -> str:
    name = name.lower().strip()
    return ALIASES.get(name, name)


def resolve_api_key(provider: str) -> str:
    """Provider-specific key, with the generic LLM_API_KEY as override."""
    if settings.llm_api_key:
        return settings.llm_api_key
    return {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_api_key,
    }.get(provider, "")


def package_installed(info: ProviderInfo) -> bool:
    if not info.module:
        return True
    return importlib.util.find_spec(info.module) is not None


# --- Active provider state (process-wide) -----------------------------------

@dataclass(frozen=True)
class ActiveLLM:
    provider: str  # canonical name, "" = none
    model: str  # "" = provider default


_active: ActiveLLM | None = None


def get_active() -> ActiveLLM:
    """The runtime-activated provider, falling back to environment config."""
    if _active is not None:
        return _active
    return ActiveLLM(
        provider=canonical_name(settings.llm_provider),
        model=settings.llm_model,
    )


def set_active(provider: str, model: str = "") -> ActiveLLM:
    global _active
    _active = ActiveLLM(provider=canonical_name(provider), model=model)
    return _active


def reset_active() -> None:
    """Revert to environment configuration (used by tests)."""
    global _active
    _active = None
