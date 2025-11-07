"""LLM client abstractions."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from openai import OpenAI

from .config import InsightAgentSettings, get_settings


class BaseLLMClient:
    """Abstract interface used by the LangGraph orchestrator."""

    def generate(self, prompt: str, **kwargs: Any) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    def __init__(self, settings: Optional[InsightAgentSettings] = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIClient")
        self._client = OpenAI(api_key=self.settings.openai_api_key)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        completion = self._client.responses.create(
            model=self.settings.model,
            input=prompt,
            temperature=kwargs.get("temperature", self.settings.temperature),
            max_output_tokens=kwargs.get("max_tokens", self.settings.max_tokens),
        )
        # Adapt to responses API structure
        if not completion.output:
            return ""
        text_chunks: Iterable[str] = (
            block.text.value
            for block in completion.output
            if hasattr(block, "text") and block.text and getattr(block.text, "value", None)
        )
        return "\n".join(text_chunks)


class DummyLLM(BaseLLMClient):
    """Fallback deterministic client for unit tests and offline execution."""

    def generate(self, prompt: str, **kwargs: Any) -> str:  # pragma: no cover - trivial
        return "\n".join(["Automated insight summary:", prompt[:256]])


def build_llm_client(settings: Optional[InsightAgentSettings] = None) -> BaseLLMClient:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return OpenAIClient(settings)
    return DummyLLM()
