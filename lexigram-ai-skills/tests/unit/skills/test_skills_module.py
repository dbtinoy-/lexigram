"""Tests for skills module."""

from __future__ import annotations

import pytest

from lexigram.ai.skills import SkillsModule
from lexigram.contracts.ai.skills import SkillExecutorProtocol
from lexigram.di.module import DynamicModule


class TestSkillsModule:
    """Test suite for SkillsModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to SkillsModule."""
        assert hasattr(SkillsModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = SkillsModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is SkillsModule

    def test_configure_exports_skill_executor_protocol(self) -> None:
        """Verify configure() exports SkillExecutorProtocol."""
        result = SkillsModule.configure(None)
        assert SkillExecutorProtocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"timeout": 30}
        result = SkillsModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is SkillsModule
