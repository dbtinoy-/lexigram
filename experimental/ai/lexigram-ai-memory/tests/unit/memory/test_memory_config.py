"""Tests for memory configuration."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.config import (
    WorkingMemoryConfig,
    EpisodicMemoryConfig,
    SemanticMemoryConfig,
    MemoryConfig,
)


class TestWorkingMemoryConfigDefaults:
    """Test WorkingMemoryConfig default values."""

    def test_default_config(self) -> None:
        """Default config should have sensible values."""
        config = WorkingMemoryConfig()

        assert config.system_prompt_tokens > 0
        assert 0.0 <= config.recent_turns_fraction <= 1.0
        assert 0.0 <= config.episodic_fraction <= 1.0
        assert 0.0 <= config.semantic_fraction <= 1.0
        assert 0.0 <= config.tool_descriptions_fraction <= 1.0
        assert config.max_recent_turns >= 1

    def test_fractions_are_valid_probabilities(self) -> None:
        """All fractions should be between 0.0 and 1.0."""
        config = WorkingMemoryConfig()

        assert 0.0 <= config.recent_turns_fraction <= 1.0
        assert 0.0 <= config.episodic_fraction <= 1.0
        assert 0.0 <= config.semantic_fraction <= 1.0
        assert 0.0 <= config.tool_descriptions_fraction <= 1.0


class TestWorkingMemoryConfigCustomization:
    """Test WorkingMemoryConfig customization."""

    def test_can_customize_system_prompt_tokens(self) -> None:
        """Config should allow setting system prompt tokens."""
        config = WorkingMemoryConfig(system_prompt_tokens=2000)

        assert config.system_prompt_tokens == 2000

    def test_can_customize_fractions(self) -> None:
        """Config should allow customizing budget fractions."""
        config = WorkingMemoryConfig(
            recent_turns_fraction=0.4,
            episodic_fraction=0.3,
            semantic_fraction=0.2,
            tool_descriptions_fraction=0.1,
        )

        assert config.recent_turns_fraction == 0.4
        assert config.episodic_fraction == 0.3
        assert config.semantic_fraction == 0.2
        assert config.tool_descriptions_fraction == 0.1

    def test_can_set_max_recent_turns(self) -> None:
        """Config should allow setting max recent turns."""
        config = WorkingMemoryConfig(max_recent_turns=20)

        assert config.max_recent_turns == 20


class TestEpisodicMemoryConfigDefaults:
    """Test EpisodicMemoryConfig default values."""

    def test_default_config(self) -> None:
        """Default config should have sensible values."""
        config = EpisodicMemoryConfig()

        assert config.default_top_k >= 1
        assert config.recency_weight >= 0.0
        assert config.importance_weight >= 0.0
        assert config.relevance_weight >= 0.0


class TestEpisodicMemoryConfigCustomization:
    """Test EpisodicMemoryConfigcustomization."""

    def test_can_customize_top_k(self) -> None:
        """Config should allow setting top_k."""
        config = EpisodicMemoryConfig(default_top_k=10)

        assert config.default_top_k == 10

    def test_can_customize_weights(self) -> None:
        """Config should allow customizing scoring weights."""
        config = EpisodicMemoryConfig(
            recency_weight=0.3,
            importance_weight=0.5,
            relevance_weight=0.2,
        )

        assert config.recency_weight == 0.3
        assert config.importance_weight == 0.5
        assert config.relevance_weight == 0.2


class TestSemanticMemoryConfigDefaults:
    """Test SemanticMemoryConfig default values."""

    def test_default_config(self) -> None:
        """Default config should have sensible values."""
        config = SemanticMemoryConfig()

        assert config.min_confidence >= 0.0
        assert config.max_facts_per_entity >= 1


class TestSemanticMemoryConfigCustomization:
    """Test SemanticMemoryConfig customization."""

    def test_can_customize_top_k(self) -> None:
        """Config should allow setting min_confidence."""
        config = SemanticMemoryConfig(min_confidence=0.8)

        assert config.min_confidence == 0.8

    def test_can_enable_disable_entity_extraction(self) -> None:
        """Config should allow setting max_facts_per_entity."""
        config = SemanticMemoryConfig(max_facts_per_entity=10)

        assert config.max_facts_per_entity == 10


class TestMemoryConfigDefaults:
    """Test MemoryConfig default values."""

    def test_default_config(self) -> None:
        """Default config should have all tiers configured."""
        config = MemoryConfig()

        assert hasattr(config, "working")
        assert hasattr(config, "episodic")
        assert hasattr(config, "semantic")
        assert isinstance(config.working, WorkingMemoryConfig)
        assert isinstance(config.episodic, EpisodicMemoryConfig)
        assert isinstance(config.semantic, SemanticMemoryConfig)

    def test_consolidation_enabled_by_default(self) -> None:
        """Config should have consolidation enabled by default."""
        config = MemoryConfig()

        assert hasattr(config, "consolidation")
        assert config.consolidation.enabled is True


class TestMemoryConfigCustomization:
    """Test MemoryConfig customization."""

    def test_can_customize_working_memory(self) -> None:
        """Config should allow customizing working memory."""
        working = WorkingMemoryConfig(max_recent_turns=25)
        config = MemoryConfig(working=working)

        assert config.working.max_recent_turns == 25

    def test_can_customize_episodic_memory(self) -> None:
        """Config should allow customizing episodic memory."""
        episodic = EpisodicMemoryConfig(default_top_k=20)
        config = MemoryConfig(episodic=episodic)

        assert config.episodic.default_top_k == 20

    def test_can_customize_semantic_memory(self) -> None:
        """Config should allow customizing semantic memory."""
        semantic = SemanticMemoryConfig(default_top_k=30)
        config = MemoryConfig(semantic=semantic)

        assert config.semantic.default_top_k == 30


class TestMemoryConfigTiering:
    """Test multi-tier memory configuration."""

    def test_three_tier_structure(self) -> None:
        """Memory should have three configured tiers."""
        config = MemoryConfig()

        tiers = [config.working, config.episodic, config.semantic]
        assert len(tiers) == 3
        assert all(tier is not None for tier in tiers)

    def test_independent_tier_configuration(self) -> None:
        """Each tier should be independently configurable."""
        working = WorkingMemoryConfig(max_recent_turns=30)
        episodic = EpisodicMemoryConfig(default_top_k=25)
        semantic = SemanticMemoryConfig(default_top_k=35)

        config = MemoryConfig(
            working=working,
            episodic=episodic,
            semantic=semantic,
        )

        assert config.working.max_recent_turns == 30
        assert config.episodic.default_top_k == 25
        assert config.semantic.default_top_k == 35
