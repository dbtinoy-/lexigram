"""Unit tests for MemoryConfig."""

from __future__ import annotations

import pytest
from lexigram.validation import ValidationError  # noqa: F401 (kept for future use)

from lexigram.ai.memory.config import MemoryConfig, WorkingMemoryConfig


class TestMemoryConfig:
    def test_memory_config_model_config_has_env_prefix(self) -> None:
        mc = MemoryConfig.model_config
        assert mc.get("env_prefix") == "LEX_AI_MEMORY__"
        assert mc.get("env_nested_delimiter") == "__"

    def test_default_config_values(self) -> None:
        config = MemoryConfig()

        assert config.enabled is True
        assert config.default_backend == "in_memory"
        assert config.ttl_seconds == 86400 * 30
        assert isinstance(config.working, WorkingMemoryConfig)

    def test_config_accepts_custom_values(self) -> None:
        config = MemoryConfig(
            enabled=False,
            default_backend="cache",
            ttl_seconds=3600,
        )

        assert config.enabled is False
        assert config.default_backend == "cache"
        assert config.ttl_seconds == 3600

    def test_config_validation_fails_on_negative(self) -> None:
        with pytest.raises(ValueError):
            MemoryConfig(ttl_seconds=-1)

    def test_working_memory_config_defaults(self) -> None:
        config = MemoryConfig()
        working = config.working

        assert working.system_prompt_tokens == 512
        assert working.recent_turns_fraction == 0.40
        assert working.episodic_fraction == 0.30
        assert working.semantic_fraction == 0.20
        assert working.tool_descriptions_fraction == 0.10
        assert working.max_recent_turns == 20

    def test_working_config_validates_fraction_bounds(self) -> None:
        with pytest.raises(ValueError):
            WorkingMemoryConfig(recent_turns_fraction=1.5)
