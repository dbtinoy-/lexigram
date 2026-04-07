"""Tests for hooks module payload classes."""

import pytest

from lexigram.ai.observability.hooks import (
    AIObservabilityStartedHook,
    HealthCheckRunHook,
    LLMCallTracedHook,
)


class TestAIObservabilityStartedHook:
    """Test AIObservabilityStartedHook."""

    def test_creation(self):
        hook = AIObservabilityStartedHook()
        assert hook is not None


class TestLLMCallTracedHook:
    """Test LLMCallTracedHook."""

    def test_creation_with_attributes(self):
        hook = LLMCallTracedHook(provider="openai", model="gpt-4")
        assert hook.provider == "openai"
        assert hook.model == "gpt-4"

    def test_is_frozen(self):
        hook = LLMCallTracedHook(provider="openai", model="gpt-4")
        assert hook.provider == "openai"
        assert hook.model == "gpt-4"
        assert hook.__class__.__dataclass_fields__["provider"].kw_only is True


class TestHealthCheckRunHook:
    """Test HealthCheckRunHook."""

    def test_creation_with_attributes(self):
        hook = HealthCheckRunHook(component="llm", healthy=True)
        assert hook.component == "llm"
        assert hook.healthy is True

    def test_creation_unhealthy(self):
        hook = HealthCheckRunHook(component="vector", healthy=False)
        assert hook.component == "vector"
        assert hook.healthy is False

    def test_is_frozen(self):
        hook = HealthCheckRunHook(component="llm", healthy=True)
        assert hook.__class__.__dataclass_fields__["component"].kw_only is True