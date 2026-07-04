"""LLM provider selection and call hardening (timeout + one retry)."""

import asyncio

from app.core.config import settings
from app.core.exceptions import LLMNotConfiguredError
from app.core.logging import AppLogger
from app.ai.llm.provider import LLMProvider, PromptPayload, LLMResult, FakeLLMProvider

logger = AppLogger("LLMClient")


def get_llm_provider() -> LLMProvider:
    """Return the configured provider.

    Only 'fake' exists today; real adapters (anthropic/openai/...) register
    here when a provider is chosen. Unset/unknown -> explicit 503-style error
    rather than a silent fallback.
    """
    name = settings.llm_provider.lower().strip()
    if name == "fake":
        return FakeLLMProvider(canned_response=settings.llm_fake_response)
    raise LLMNotConfiguredError(provider=name or "<unset>")


async def complete_with_retry(
    provider: LLMProvider, payload: PromptPayload, timeout_s: float = 30.0
) -> LLMResult:
    """One call, one retry on failure/timeout. Deliberately simple; a real
    backoff policy comes with the first production provider."""
    try:
        return await asyncio.wait_for(provider.complete(payload), timeout=timeout_s)
    except Exception as first_error:
        logger.warning(f"LLM call failed, retrying once: {first_error}")
        return await asyncio.wait_for(provider.complete(payload), timeout=timeout_s)
