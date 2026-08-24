"""Tests for AIModule.configure."""

from __future__ import annotations


class TestAIModuleConfigure:
    """Additional tests for AIModule.configure()."""

    def test_configure_with_ai_config(self) -> None:
        from lexigram.ai.config import AIConfig
        from lexigram.ai.module import AIModule
        from lexigram.di.module import DynamicModule

        config = AIConfig()
        result = AIModule.configure(config)
        assert isinstance(result, DynamicModule)

    def test_configure_provider_is_ai_provider(self) -> None:
        from lexigram.ai.di.provider import AIProvider
        from lexigram.ai.module import AIModule

        result = AIModule.configure(None)
        assert any(isinstance(p, AIProvider) for p in result.providers)

    def test_configure_with_kwargs(self) -> None:
        from lexigram.ai.module import AIModule
        from lexigram.di.module import DynamicModule

        result = AIModule.configure(None, name="custom-ai")
        assert isinstance(result, DynamicModule)
