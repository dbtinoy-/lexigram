"""Configuration schemas for Lexigram Intelligence.

This module defines Pydantic models for configuring LLM providers,
vector stores, and ML components.

Example:
    from lexigram.ai.config import AIConfig

    # From YAML
    config = AIConfig.from_yaml("application.yaml")

    # From environment
    config = AIConfig()  # reads LEX_AI__* env vars
"""

from __future__ import annotations

from typing import Any, ClassVar

from lexigram.ai import constants as const
from lexigram.config import BaseConfig
from lexigram.contracts.core.provider import ProviderProtocol
from lexigram.validation import ConfigDict, Field, model_validator

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = const.ENV_PREFIX
ENV_NESTED_DELIMITER: str = const.ENV_NESTED_DELIMITER


class _DisabledSubsystem:
    """Sentinel config returned when an optional AI sub-package is not installed."""

    enabled = False

    def __bool__(self) -> bool:
        return False

    def __getattr__(self, name: str) -> None:
        return None


try:
    from lexigram.ai.llm.config import ClientConfig
except ImportError:
    ClientConfig = None  # type: ignore[assignment, misc]

try:
    from lexigram.vector.config import VectorConfig
except ImportError:
    VectorConfig = None  # type: ignore[assignment, misc]

try:
    from lexigram.ai.rag.config import RAGConfig
except ImportError:
    RAGConfig = None  # type: ignore[assignment, misc]

try:
    from lexigram.ai.governance.config import GovernanceConfig
except ImportError:
    GovernanceConfig = None  # type: ignore[assignment, misc]

try:
    from lexigram.ai.observability.config import ObservabilityConfig
except ImportError:
    ObservabilityConfig = None  # type: ignore[assignment, misc]


class AIConfig(BaseConfig):
    """Complete configuration for Lexigram Intelligence.

    Attributes:
        name: Configuration name (default: "ai")
        enabled: Whether AI features are enabled
        llm: LLM configuration
        vector: Vector store configuration
        rag: RAG pipeline configuration
        governance: AI governance configuration
        observability: Observability configuration
        subsystems: Dynamic configuration for third-party AI subsystems
    """

    config_section: ClassVar[str] = "ai"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    name: str = Field(default="ai", description="Configuration name")
    enabled: bool = Field(default=True, description="Enable AI features")
    llm: Any | None = Field(
        default=None,
        description="LLM configuration (optional)",
    )
    # Vector configuration is optional - avoid requiring a default provider
    # that pulls in external dependencies (e.g., Chroma) during simple test runs.
    vector: Any | None = Field(
        default=None,
        description="Vector store configuration",
    )
    rag: Any | None = Field(
        default=None,
        description="RAG pipeline configuration (optional)",
    )
    governance: Any = Field(
        default_factory=lambda: (
            GovernanceConfig() if GovernanceConfig is not None else _DisabledSubsystem()
        ),
        description="AI governance configuration",
    )
    observability: Any = Field(
        default_factory=lambda: (
            ObservabilityConfig()
            if ObservabilityConfig is not None
            else _DisabledSubsystem()
        ),
        description="AI observability configuration (tracing and metrics)",
    )
    subsystems: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Dynamic configuration for third-party AI subsystems discovered "
            "via entry points.  Keys are subsystem names; values are their "
            "configuration dictionaries."
        ),
    )

    @classmethod
    def get_provider_class(cls) -> type[ProviderProtocol]:
        """Return the provider class for this config."""
        from lexigram.ai import AIProvider

        return AIProvider

    @model_validator(mode="after")
    def validate_production_security(self) -> AIConfig:
        """Block insecure AI configurations in production."""
        import os

        env = os.getenv("LEX_ENV", "development").lower()
        if env == "production":
            if self.llm and self.llm.api_key:
                key_value = self.llm.api_key.get_secret_value()
                insecure_defaults = ("sk-...", "sk-test", "change-me")
                if any(
                    key_value.startswith(d) or d in key_value.lower()
                    for d in insecure_defaults
                ):
                    raise ValueError(
                        "CRITICAL SECURITY ERROR: Insecure LLM API key detected in PRODUCTION.\n"
                        "You MUST set a valid API key via LEX_AI_LLM__API_KEY.",
                    )
        return self


def get_subsystem_config(
    ai_config: AIConfig,
    subsystem_name: str,
    default: Any = None,
) -> Any:
    """Get configuration for a dynamically discovered AI subsystem.

    First checks the known top-level fields (``llm``, ``vector``, ``rag``,
    ``governance``, ``observability``).  Falls back to the ``subsystems``
    dict for third-party subsystems registered via entry points.

    Args:
        ai_config: The root AI configuration.
        subsystem_name: Name of the subsystem (e.g. ``"llm"``, ``"fine_tuning"``).
        default: Value returned when the subsystem has no configuration.

    Returns:
        The subsystem's configuration object or dict, or *default*.
    """
    # Built-in subsystems are explicit fields
    if hasattr(ai_config, subsystem_name):
        value = getattr(ai_config, subsystem_name)
        if value is not None:
            return value
    # Dynamic subsystems live in the subsystems dict
    return ai_config.subsystems.get(subsystem_name, default)


try:
    # RAG pipeline detail configs — available when lexigram-ai-rag is installed
    from lexigram.ai.rag.config import (
        ContextOptimizationConfig,
        DocumentFormat,
        IngestionConfig,
        PipelineConfig,
        PipelineStageType,
        PostProcessingConfig,
        QualityAssuranceConfig,
        QueryProcessingConfig,
        RetrievalConfig,
        RoutingStrategyType,
        SynthesisConfig,
    )
except ImportError:
    ContextOptimizationConfig = None  # type: ignore[assignment, misc]
    DocumentFormat = None  # type: ignore[assignment, misc]
    IngestionConfig = None  # type: ignore[assignment, misc]
    PipelineConfig = None  # type: ignore[assignment, misc]
    PipelineStageType = None  # type: ignore[assignment, misc]
    PostProcessingConfig = None  # type: ignore[assignment, misc]
    QualityAssuranceConfig = None  # type: ignore[assignment, misc]
    QueryProcessingConfig = None  # type: ignore[assignment, misc]
    RetrievalConfig = None  # type: ignore[assignment, misc]
    RoutingStrategyType = None  # type: ignore[assignment, misc]
    SynthesisConfig = None  # type: ignore[assignment, misc]

__all__ = [
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "AIConfig",
    "get_subsystem_config",
]
