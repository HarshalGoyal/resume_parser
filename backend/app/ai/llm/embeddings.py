"""Embeddings abstraction for peer benchmarking / vector search.

Same shape as the chat-LLM layer: a small protocol, a deterministic fake for
tests and local development, and LangChain-backed adapters whose provider
packages are imported lazily. Note Anthropic offers no embeddings API, so the
real choices are openai / google / bedrock.
"""

import hashlib
import math
from typing import Protocol

from app.core.config import settings
from app.core.exceptions import LLMNotConfiguredError


class EmbeddingsProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddings:
    """Deterministic, offline embeddings: token-hash bag-of-words.

    Similar texts (shared tokens) produce similar vectors, which is exactly
    what benchmarking tests need - no network, no keys, stable across runs.
    """

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class LangChainEmbeddings:
    """Adapter over a LangChain Embeddings implementation."""

    def __init__(self, lc_embeddings):
        self._lc = lc_embeddings

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._lc.aembed_documents(texts)


def get_embeddings_provider() -> EmbeddingsProvider:
    """Build the embeddings provider selected by EMBEDDINGS_PROVIDER."""
    name = settings.embeddings_provider.lower().strip()
    model = settings.embeddings_model

    if name == "fake":
        return FakeEmbeddings()

    if name == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as e:
            raise LLMNotConfiguredError(
                provider="openai-embeddings", hint="pip install langchain-openai"
            ) from e
        return LangChainEmbeddings(
            OpenAIEmbeddings(
                model=model or "text-embedding-3-small",
                api_key=settings.openai_api_key or settings.llm_api_key,
            )
        )

    if name in ("google", "gemini"):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as e:
            raise LLMNotConfiguredError(
                provider="google-embeddings", hint="pip install langchain-google-genai"
            ) from e
        return LangChainEmbeddings(
            GoogleGenerativeAIEmbeddings(
                model=model or "models/text-embedding-004",
                google_api_key=settings.google_api_key or settings.llm_api_key,
            )
        )

    if name in ("bedrock", "aws"):
        try:
            from langchain_aws import BedrockEmbeddings
        except ImportError as e:
            raise LLMNotConfiguredError(
                provider="bedrock-embeddings", hint="pip install langchain-aws"
            ) from e
        return LangChainEmbeddings(
            BedrockEmbeddings(model_id=model or "amazon.titan-embed-text-v2:0")
        )

    raise LLMNotConfiguredError(
        provider=name or "<unset>",
        hint="set EMBEDDINGS_PROVIDER to fake | openai | google | bedrock",
    )
