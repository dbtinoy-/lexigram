"""Tests for Prompt module."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt import PromptModule
from lexigram.ai.prompt.config import PromptConfig
from lexigram.contracts.ai.llm import PromptTemplateProtocol
from lexigram.di.module import DynamicModule


class TestPromptModule:
    """Test suite for PromptModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to PromptModule."""
        assert hasattr(PromptModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = PromptModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is PromptModule

    def test_configure_exports_prompt_template_protocol(self) -> None:
        """Verify configure() exports PromptTemplateProtocol."""
        result = PromptModule.configure(None)
        assert PromptTemplateProtocol in result.exports

    def test_configure_with_config(self) -> None:
        """Verify configure() accepts PromptConfig."""
        config = PromptConfig()
        result = PromptModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is PromptModule

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"max_tokens": 2000}
        result = PromptModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is PromptModule
