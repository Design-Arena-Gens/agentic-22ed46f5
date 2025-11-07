"""Configuration objects for the InsightAgent engine."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InsightAgentSettings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-mini")
    temperature: float = 0.2
    max_tokens: int = 1024

    model_config = SettingsConfigDict(env_prefix="INSIGHT_AGENT_", extra="allow")


@lru_cache(maxsize=1)
def get_settings() -> InsightAgentSettings:
    return InsightAgentSettings()  # type: ignore[arg-type]
