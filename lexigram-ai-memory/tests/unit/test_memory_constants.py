"""Unit tests for memory constants module."""

from __future__ import annotations

import pytest


class TestConstantsExports:
    """Test that constants are exported correctly."""

    def test_exports_all_constants(self) -> None:
        from lexigram.ai.memory.constants import __all__
        assert len(__all__) > 0
        assert "DEFAULT_BACKEND" in __all__


class TestEnvironmentConstants:
    """Test environment variable prefix constants."""

    def test_env_prefix(self) -> None:
        from lexigram.ai.memory.constants import ENV_PREFIX
        assert isinstance(ENV_PREFIX, str)
        assert ENV_PREFIX.startswith("LEX_")

    def test_nested_delimiter(self) -> None:
        from lexigram.ai.memory.constants import ENV_NESTED_DELIMITER
        assert isinstance(ENV_NESTED_DELIMITER, str)
        assert ENV_NESTED_DELIMITER == "__"


class TestWorkingMemoryDefaults:
    """Test working memory default constants."""

    def test_default_system_prompt_tokens(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_SYSTEM_PROMPT_TOKENS
        assert isinstance(DEFAULT_SYSTEM_PROMPT_TOKENS, int)
        assert DEFAULT_SYSTEM_PROMPT_TOKENS > 0

    def test_default_recent_turns_fraction(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_RECENT_TURNS_FRACTION
        assert 0.0 <= DEFAULT_RECENT_TURNS_FRACTION <= 1.0

    def test_default_episodic_fraction(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_EPISODIC_FRACTION
        assert 0.0 <= DEFAULT_EPISODIC_FRACTION <= 1.0

    def test_default_semantic_fraction(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_SEMANTIC_FRACTION
        assert 0.0 <= DEFAULT_SEMANTIC_FRACTION <= 1.0

    def test_default_tool_desc_fraction(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_TOOL_DESC_FRACTION
        assert 0.0 <= DEFAULT_TOOL_DESC_FRACTION <= 1.0

    def test_default_max_recent_turns(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_MAX_RECENT_TURNS
        assert isinstance(DEFAULT_MAX_RECENT_TURNS, int)
        assert DEFAULT_MAX_RECENT_TURNS > 0


class TestEpisodicMemoryDefaults:
    """Test episodic memory default constants."""

    def test_default_episodic_top_k(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_EPISODIC_TOP_K
        assert isinstance(DEFAULT_EPISODIC_TOP_K, int)
        assert DEFAULT_EPISODIC_TOP_K > 0

    def test_default_recency_weight(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_RECENCY_WEIGHT
        assert 0.0 <= DEFAULT_RECENCY_WEIGHT <= 1.0

    def test_default_importance_weight(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_IMPORTANCE_WEIGHT
        assert 0.0 <= DEFAULT_IMPORTANCE_WEIGHT <= 1.0

    def test_default_relevance_weight(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_RELEVANCE_WEIGHT
        assert 0.0 <= DEFAULT_RELEVANCE_WEIGHT <= 1.0

    def test_default_episodic_ttl_seconds(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_EPISODIC_TTL_SECONDS
        assert isinstance(DEFAULT_EPISODIC_TTL_SECONDS, int)
        assert DEFAULT_EPISODIC_TTL_SECONDS >= 0


class TestSemanticMemoryDefaults:
    """Test semantic memory default constants."""

    def test_default_min_confidence(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_MIN_CONFIDENCE
        assert 0.0 <= DEFAULT_MIN_CONFIDENCE <= 1.0

    def test_default_max_facts_per_entity(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_MAX_FACTS_PER_ENTITY
        assert isinstance(DEFAULT_MAX_FACTS_PER_ENTITY, int)
        assert DEFAULT_MAX_FACTS_PER_ENTITY > 0


class TestConsolidationDefaults:
    """Test consolidation default constants."""

    def test_default_consolidation_interval_s(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_CONSOLIDATION_INTERVAL_S
        assert isinstance(DEFAULT_CONSOLIDATION_INTERVAL_S, float)
        assert DEFAULT_CONSOLIDATION_INTERVAL_S > 0

    def test_default_consolidation_age_threshold_hours(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS
        assert isinstance(DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS, float)
        assert DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS > 0

    def test_default_consolidation_importance_prune(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE
        assert 0.0 <= DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE <= 1.0

    def test_default_consolidation_batch_size(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_CONSOLIDATION_BATCH_SIZE
        assert isinstance(DEFAULT_CONSOLIDATION_BATCH_SIZE, int)
        assert DEFAULT_CONSOLIDATION_BATCH_SIZE > 0


class TestRootConfigDefaults:
    """Test root config default constants."""

    def test_default_backend(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_BACKEND
        assert isinstance(DEFAULT_BACKEND, str)
        assert len(DEFAULT_BACKEND) > 0

    def test_default_ttl_seconds(self) -> None:
        from lexigram.ai.memory.constants import DEFAULT_TTL_SECONDS
        assert isinstance(DEFAULT_TTL_SECONDS, int)
        assert DEFAULT_TTL_SECONDS > 0


class TestVersionConstant:
    """Test __version__ constant."""

    def test_version_exists(self) -> None:
        from lexigram.ai.memory.constants import __version__
        assert isinstance(__version__, str)

    def test_version_format(self) -> None:
        from lexigram.ai.memory.constants import __version__
        parts = __version__.split(".")
        assert len(parts) >= 2


class TestAllExportsList:
    """Test __all__ contains expected exports."""

    def test_all_contains_expected_items(self) -> None:
        from lexigram.ai.memory.constants import __all__
        expected = [
            "DEFAULT_BACKEND",
            "DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS",
            "DEFAULT_CONSOLIDATION_BATCH_SIZE",
            "DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE",
            "DEFAULT_CONSOLIDATION_INTERVAL_S",
            "DEFAULT_EPISODIC_FRACTION",
            "DEFAULT_EPISODIC_TOP_K",
            "DEFAULT_EPISODIC_TTL_SECONDS",
            "DEFAULT_IMPORTANCE_WEIGHT",
            "DEFAULT_MAX_FACTS_PER_ENTITY",
            "DEFAULT_MAX_RECENT_TURNS",
            "DEFAULT_MIN_CONFIDENCE",
            "DEFAULT_RECENCY_WEIGHT",
            "DEFAULT_RECENT_TURNS_FRACTION",
            "DEFAULT_RELEVANCE_WEIGHT",
            "DEFAULT_SEMANTIC_FRACTION",
            "DEFAULT_SYSTEM_PROMPT_TOKENS",
            "DEFAULT_TOOL_DESC_FRACTION",
            "DEFAULT_TTL_SECONDS",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "__version__",
        ]
        for item in expected:
            assert item in __all__, f"Missing {item} in __all__"