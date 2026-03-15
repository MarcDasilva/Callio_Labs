from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    model_name: str = "default"
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 120

    model_config = {"env_prefix": "LLM_"}


class LLMPurposeMap(BaseSettings):
    """Per-purpose overrides.  Falls back to LLMConfig defaults."""

    search_model: str = Field("default", alias="LLM_SEARCH_MODEL")
    hypothesis_model: str = Field("default", alias="LLM_HYPOTHESIS_MODEL")
    judge_model: str = Field("default", alias="LLM_JUDGE_MODEL")
    response_model: str = Field("default", alias="LLM_RESPONSE_MODEL")

    model_config = {"populate_by_name": True}


class Settings(BaseSettings):
    llm_provider: str = Field(
        "fake",
        description="LLM provider identifier (e.g. 'openai', 'anthropic', 'ollama', 'fake')",
    )
    llm: LLMConfig = LLMConfig()
    llm_purposes: LLMPurposeMap = LLMPurposeMap()

    default_max_iterations: int = 3
    mock_retrieval: bool = True

    log_level: str = "INFO"

    # Primer3 design service (for proxy); set to empty to disable proxy.
    primer3_base_url: str = Field(
        "http://127.0.0.1:8001",
        description="Base URL of the Primer3 design service for design-from-alignment proxy.",
    )

    model_config = {"env_prefix": "APP_", "env_nested_delimiter": "__"}


settings = Settings()
