"""Concrete LLM provider adapters built on LangChain chat models.

One abstract base implements the platform's LLMProvider protocol (payload ->
messages, usage extraction, timing); each provider subclass only knows how to
construct its LangChain chat model. Provider packages are imported lazily so
the application runs without any of them installed - you only need the package
for the provider you actually configure:

    anthropic -> pip install langchain-anthropic
    openai    -> pip install langchain-openai
    google    -> pip install langchain-google-genai
    bedrock   -> pip install langchain-aws
"""

import time
from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.llm.provider import PromptPayload, LLMResult
from app.core.exceptions import LLMNotConfiguredError
from app.core.logging import AppLogger

logger = AppLogger("LLMAdapters")


class BaseLangChainAdapter(ABC):
    """Implements LLMProvider once for every LangChain-backed provider."""

    #: model used when LLM_MODEL is not configured
    default_model: str = ""

    def __init__(self, model: str = "", api_key: str = ""):
        self.model = model or self.default_model
        self.api_key = api_key
        self._chat_model: BaseChatModel | None = None

    @abstractmethod
    def build_chat_model(self, max_tokens: int, temperature: float) -> BaseChatModel:
        """Construct the provider-specific LangChain chat model."""

    async def complete(self, payload: PromptPayload) -> LLMResult:
        if self._chat_model is None:
            self._chat_model = self.build_chat_model(
                max_tokens=payload.max_tokens, temperature=payload.temperature
            )

        messages = [
            SystemMessage(content=payload.system),
            HumanMessage(content=payload.user_content),
        ]
        started = time.monotonic()
        response = await self._chat_model.ainvoke(messages)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        usage = getattr(response, "usage_metadata", None) or {}
        text = response.content if isinstance(response.content, str) else str(response.content)
        return LLMResult(
            text=text,
            model=self.model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=elapsed_ms,
        )

    def _missing_package(self, package: str, error: Exception) -> LLMNotConfiguredError:
        logger.error(f"LLM provider package missing: {package} ({error})")
        return LLMNotConfiguredError(
            provider=type(self).__name__,
            hint=f"pip install {package}",
        )


class AnthropicAdapter(BaseLangChainAdapter):
    default_model = "claude-opus-4-8"

    def build_chat_model(self, max_tokens: int, temperature: float) -> BaseChatModel:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise self._missing_package("langchain-anthropic", e) from e
        return ChatAnthropic(
            model=self.model, api_key=self.api_key, max_tokens=max_tokens
        )


class OpenAIAdapter(BaseLangChainAdapter):
    default_model = "gpt-4o"

    def build_chat_model(self, max_tokens: int, temperature: float) -> BaseChatModel:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise self._missing_package("langchain-openai", e) from e
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )


class GeminiAdapter(BaseLangChainAdapter):
    default_model = "gemini-2.0-flash"

    def build_chat_model(self, max_tokens: int, temperature: float) -> BaseChatModel:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise self._missing_package("langchain-google-genai", e) from e
        return ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self.api_key,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )


class BedrockAdapter(BaseLangChainAdapter):
    # Bedrock model IDs carry the provider prefix.
    default_model = "anthropic.claude-opus-4-8"

    def build_chat_model(self, max_tokens: int, temperature: float) -> BaseChatModel:
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as e:
            raise self._missing_package("langchain-aws", e) from e
        # Credentials/region resolve via the standard AWS chain
        # (env vars, profile, instance role); no api_key involved.
        return ChatBedrockConverse(
            model=self.model, max_tokens=max_tokens, temperature=temperature
        )
