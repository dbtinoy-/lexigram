"""Configuration schema for the LLM package.

Defines LLMConfig, the typed configuration object accepted by LLMProvider
and all LLM client implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from lexigram.ai.llm.pinning import ModelPinPolicy
from lexigram.config.base import BaseConfig
from lexigram.contracts.ai.types import ModelProvider
from lexigram.validation import ConfigDict, Field, SecretStr

if TYPE_CHECKING:
    from lexigram.contracts.ai.thinking import ThinkingConfig


@dataclass(init=False)
class ClientConfig(BaseConfig):
    """Configuration for LLM clients.

    Example:
        >>> config = ClientConfig(
        ...     provider="openai",
        ...     model="gpt-4-turbo",
        ...     api_key="sk-...",
        ...     temperature=0.7,
        ...     max_tokens=2000,
        ... )
    """

    config_section: ClassVar[str] = "ai_llm"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    enabled: bool = Field(default=True, description="Enable the LLM subsystem")

    provider: ModelProvider = Field(
        default=ModelProvider.OPENAI,
        description="LLM provider name.",
    )
    model: str = Field(default="gpt-4-turbo", description="Model name or identifier.")
    model_revision: str | None = Field(
        default=None,
        description="Pinned model revision (provider-specific, e.g. date or version string).",
    )
    pin_policy: ModelPinPolicy = Field(
        default=ModelPinPolicy.LATEST,
        description="Policy for enforcing the model revision pin.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="API key for the chosen provider.",
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL (for Azure, local, or proxied endpoints).",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature.",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens in response.",
    )
    timeout: float = Field(
        default=60.0,
        ge=1.0,
        description="Request timeout in seconds.",
    )
    enable_cache: bool = Field(
        default=False,
        description="Enable response caching (requires CacheBackendProtocol in container).",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds.",
    )
    thinking: ThinkingConfig | None = Field(
        default=None,
        description=(
            "Thinking/reasoning configuration.  ``None`` disables thinking. "
            "Set to a ``ThinkingConfig`` instance to enable provider-appropriate "
            "reasoning output (Anthropic extended thinking, Gemini thinking, "
            "OpenAI reasoning effort, Bedrock Claude reasoning, OpenRouter reasoning)."
        ),
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific extra parameters passed verbatim.",
    )

    def __post_init__(self) -> None:
        """Coerce provider string to ModelProvider enum and api_key to SecretStr."""
        if isinstance(self.provider, str):
            self.provider = ModelProvider(self.provider)
        api_key: Any = self.api_key
        if api_key is not None and not isinstance(api_key, SecretStr):
            self.api_key = SecretStr(api_key)


__all__ = ["ClientConfig"]
