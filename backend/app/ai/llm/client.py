"""LLM provider selection and call hardening (timeout + one retry)."""

import asyncio
from typing import Callable

from app.core.config import settings
from app.core.exceptions import BaseResumeException, LLMNotConfiguredError
from app.core.logging import AppLogger
from app.ai.llm.provider import LLMProvider, PromptPayload, LLMResult, FakeLLMProvider
from app.ai.llm.registry import PROVIDERS, get_active, resolve_api_key

logger = AppLogger("LLMClient")


def get_llm_provider() -> LLMProvider:
    """Return the currently active provider (runtime activation via
    POST /llm/activate, else the LLM_PROVIDER environment setting).

    Real providers are LangChain-backed adapters (see adapters.py); their
    packages are imported lazily, so only the active provider's package needs
    to be installed. Unset/unknown -> explicit 503-style error rather than a
    silent fallback.
    """
    active = get_active()
    name = active.provider

    if name == "fake":
        return FakeLLMProvider(canned_response=settings.llm_fake_response)

    if name in PROVIDERS:
        from app.ai.llm.adapters import (
            AnthropicAdapter,
            OpenAIAdapter,
            GeminiAdapter,
            BedrockAdapter,
        )

        adapters: dict[str, Callable[..., LLMProvider]] = {
            "anthropic": AnthropicAdapter,
            "openai": OpenAIAdapter,
            "google": GeminiAdapter,
            "bedrock": BedrockAdapter,
        }
        return adapters[name](model=active.model, api_key=resolve_api_key(name))

    raise LLMNotConfiguredError(provider=name or "<unset>")


async def complete_with_retry(
    provider: LLMProvider, payload: PromptPayload, timeout_s: float = 30.0
) -> LLMResult:
    """One call, one retry on transient failure/timeout. Configuration errors
    (missing package/provider) are never retried."""
    try:
        return await asyncio.wait_for(provider.complete(payload), timeout=timeout_s)
    except BaseResumeException:
        raise
    except Exception as first_error:
        logger.warning(f"LLM call failed, retrying once: {first_error}")
        return await asyncio.wait_for(provider.complete(payload), timeout=timeout_s)
