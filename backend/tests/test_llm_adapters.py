"""Tests for the LangChain-backed provider adapters and the factory."""

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.ai.llm.adapters import (
    BaseLangChainAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    GeminiAdapter,
    BedrockAdapter,
)
from app.ai.llm.client import get_llm_provider
from app.ai.llm.provider import PromptPayload, FakeLLMProvider
from app.core.config import settings
from app.core.exceptions import LLMNotConfiguredError


class StubAdapter(BaseLangChainAdapter):
    """Adapter wired to a langchain fake chat model - no network, no package."""

    default_model = "stub-model"

    def build_chat_model(self, max_tokens: int, temperature: float):
        return FakeListChatModel(responses=['{"ok": true}'])


def _payload() -> PromptPayload:
    return PromptPayload(system="You are a test.", user_content="Evaluate this.")


def test_base_adapter_maps_payload_and_returns_result():
    adapter = StubAdapter()
    result = asyncio.run(adapter.complete(_payload()))
    assert result.text == '{"ok": true}'
    assert result.model == "stub-model"
    assert result.latency_ms >= 0


def test_adapter_default_models():
    assert AnthropicAdapter().model == "claude-opus-4-8"
    assert OpenAIAdapter().model == "gpt-4o"
    assert GeminiAdapter().model == "gemini-2.0-flash"
    assert BedrockAdapter().model == "anthropic.claude-opus-4-8"
    # Explicit model overrides the default.
    assert AnthropicAdapter(model="claude-sonnet-5").model == "claude-sonnet-5"


@pytest.mark.parametrize(
    "adapter_cls, package",
    [
        (AnthropicAdapter, "langchain-anthropic"),
        (OpenAIAdapter, "langchain-openai"),
        (GeminiAdapter, "langchain-google-genai"),
        (BedrockAdapter, "langchain-aws"),
    ],
)
def test_missing_provider_package_raises_with_install_hint(adapter_cls, package):
    # CI installs only langchain-core, so building any real chat model must
    # fail with a clear, actionable install hint instead of an ImportError.
    adapter = adapter_cls(api_key="test-key")
    with pytest.raises(LLMNotConfiguredError) as exc_info:
        asyncio.run(adapter.complete(_payload()))
    assert f"pip install {package}" in str(exc_info.value)


@pytest.mark.parametrize(
    "name, adapter_cls",
    [
        ("anthropic", AnthropicAdapter),
        ("openai", OpenAIAdapter),
        ("google", GeminiAdapter),
        ("gemini", GeminiAdapter),
        ("bedrock", BedrockAdapter),
        ("aws", BedrockAdapter),
    ],
)
def test_factory_returns_matching_adapter(monkeypatch, name, adapter_cls):
    monkeypatch.setattr(settings, "llm_provider", name)
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    provider = get_llm_provider()
    assert isinstance(provider, adapter_cls)


def test_factory_fake_and_unset(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")
    assert isinstance(get_llm_provider(), FakeLLMProvider)

    monkeypatch.setattr(settings, "llm_provider", "")
    with pytest.raises(LLMNotConfiguredError):
        get_llm_provider()

    monkeypatch.setattr(settings, "llm_provider", "no-such-provider")
    with pytest.raises(LLMNotConfiguredError):
        get_llm_provider()


def test_factory_passes_configured_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_model", "claude-sonnet-5")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    provider = get_llm_provider()
    assert provider.model == "claude-sonnet-5"
