"""Configuration for lexigram-ai-memory."""

from __future__ import annotations

from typing import ClassVar

from lexigram.ai.memory import constants as const
from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field


class WorkingMemoryConfig(BaseConfig):
    """Token-budget allocation for working memory assembly.

    Attributes:
        system_prompt_tokens: Fixed token allocation for system prompt.
        recent_turns_fraction: Fraction of remaining budget for recent turns.
        episodic_fraction: Fraction of remaining budget for episodic recall.
        semantic_fraction: Fraction of remaining budget for semantic facts.
        tool_descriptions_fraction: Fraction of remaining budget for tool descriptions.
        max_recent_turns: Hard cap on recent turns regardless of budget.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    system_prompt_tokens: int = Field(
        default=const.DEFAULT_SYSTEM_PROMPT_TOKENS,
        description="Fixed token allocation for system prompt",
    )
    recent_turns_fraction: float = Field(
        default=const.DEFAULT_RECENT_TURNS_FRACTION,
        ge=0.0,
        le=1.0,
        description="Fraction of remaining budget for recent turns",
    )
    episodic_fraction: float = Field(
        default=const.DEFAULT_EPISODIC_FRACTION,
        ge=0.0,
        le=1.0,
        description="Fraction of remaining budget for episodic recall",
    )
    semantic_fraction: float = Field(
        default=const.DEFAULT_SEMANTIC_FRACTION,
        ge=0.0,
        le=1.0,
        description="Fraction of remaining budget for semantic facts",
    )
    tool_descriptions_fraction: float = Field(
        default=const.DEFAULT_TOOL_DESC_FRACTION,
        ge=0.0,
        le=1.0,
        description="Fraction of remaining budget for tool descriptions",
    )
    max_recent_turns: int = Field(
        default=const.DEFAULT_MAX_RECENT_TURNS,
        ge=1,
        description="Hard cap on recent turns regardless of budget",
    )


class EpisodicMemoryConfig(BaseConfig):
    """Configuration for episodic memory tier.

    Attributes:
        default_top_k: Default number of episodes to retrieve.
        recency_weight: Weight applied to temporal recency during scoring.
        importance_weight: Weight applied to entry importance during scoring.
        relevance_weight: Weight applied to semantic similarity during scoring.
        ttl_seconds: Time-to-live for entries (0 = never expire).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    default_top_k: int = Field(
        default=const.DEFAULT_EPISODIC_TOP_K,
        ge=1,
        description="Default number of episodes to retrieve",
    )
    recency_weight: float = Field(
        default=const.DEFAULT_RECENCY_WEIGHT,
        ge=0.0,
        le=1.0,
        description="Weight applied to temporal recency during scoring",
    )
    importance_weight: float = Field(
        default=const.DEFAULT_IMPORTANCE_WEIGHT,
        ge=0.0,
        le=1.0,
        description="Weight applied to entry importance during scoring",
    )
    relevance_weight: float = Field(
        default=const.DEFAULT_RELEVANCE_WEIGHT,
        ge=0.0,
        le=1.0,
        description="Weight applied to semantic similarity during scoring",
    )
    ttl_seconds: int = Field(
        default=const.DEFAULT_EPISODIC_TTL_SECONDS,
        ge=0,
        description="Time-to-live for entries in seconds (0 = never expire)",
    )


class SemanticMemoryConfig(BaseConfig):
    """Configuration for semantic memory tier.

    Attributes:
        min_confidence: Minimum confidence to store a fact.
        max_facts_per_entity: Hard cap on stored facts per entity.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    min_confidence: float = Field(
        default=const.DEFAULT_MIN_CONFIDENCE,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score required to store a fact",
    )
    max_facts_per_entity: int = Field(
        default=const.DEFAULT_MAX_FACTS_PER_ENTITY,
        ge=1,
        description="Hard cap on stored facts per entity",
    )


class ConsolidationConfig(BaseConfig):
    """Configuration for the background consolidation pipeline.

    Attributes:
        enabled: Whether automatic consolidation is active.
        interval_seconds: How often to run a consolidation pass.
        age_threshold_hours: Minimum entry age before it can be consolidated.
        importance_prune_threshold: Entries below this importance are eligible for pruning.
        batch_size: Maximum entries processed per consolidation pass.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=True,
        description="Whether automatic background consolidation is active",
    )
    interval_seconds: float = Field(
        default=const.DEFAULT_CONSOLIDATION_INTERVAL_S,
        gt=0.0,
        description="How often to run a consolidation pass (seconds)",
    )
    age_threshold_hours: float = Field(
        default=const.DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS,
        gt=0.0,
        description="Minimum entry age (hours) before it can be consolidated",
    )
    importance_prune_threshold: float = Field(
        default=const.DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE,
        ge=0.0,
        le=1.0,
        description="Entries below this importance score are eligible for pruning",
    )
    batch_size: int = Field(
        default=const.DEFAULT_CONSOLIDATION_BATCH_SIZE,
        ge=1,
        description="Maximum entries processed per consolidation pass",
    )


ENV_PREFIX: str = const.ENV_PREFIX


class MemoryConfig(BaseConfig):
    """Top-level configuration for lexigram-ai-memory.

    Attributes:
        working: Working memory token budget configuration.
        episodic: Episodic memory retrieval configuration.
        semantic: Semantic memory fact storage configuration.
        consolidation: Background consolidation pipeline configuration.
        default_backend: Backend type to use ('in_memory', 'cache', 'database', 'vector').
        ttl_seconds: Default entry TTL in seconds (0 = never expire).
    """

    config_section: ClassVar[str] = "ai_memory"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=const.ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable the AI memory subsystem")
    name: str = "ai_memory"
    env: Environment | None = Field(None, description="Deployment environment")

    working: WorkingMemoryConfig = Field(
        default_factory=WorkingMemoryConfig,
        description="Working memory token budget configuration",
    )
    episodic: EpisodicMemoryConfig = Field(
        default_factory=EpisodicMemoryConfig,
        description="Episodic memory retrieval configuration",
    )
    semantic: SemanticMemoryConfig = Field(
        default_factory=SemanticMemoryConfig,
        description="Semantic memory fact storage configuration",
    )
    consolidation: ConsolidationConfig = Field(
        default_factory=ConsolidationConfig,
        description="Background consolidation pipeline configuration",
    )
    default_backend: str = Field(
        default=const.DEFAULT_BACKEND,
        description="Backend type to use ('in_memory', 'cache', 'database', 'vector')",
    )
    ttl_seconds: int = Field(
        default=const.DEFAULT_TTL_SECONDS,
        ge=0,
        description="Default entry TTL in seconds (0 = never expire)",
    )


__all__ = [
    "ENV_PREFIX",
    "ConsolidationConfig",
    "EpisodicMemoryConfig",
    "MemoryConfig",
    "SemanticMemoryConfig",
    "WorkingMemoryConfig",
]
