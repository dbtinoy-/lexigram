"""P2 hook surface import verification for lexigram-ai-observability."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_observability_hooks_root_module_exists() -> None:
    import lexigram.ai.observability
    from lexigram.ai.observability.hooks import (
        AIObservabilityStartedHook,
        HealthCheckRunHook,
        LLMCallTracedHook,
    )

    assert AIObservabilityStartedHook.__name__ == "AIObservabilityStartedHook"
    assert LLMCallTracedHook.__name__ == "LLMCallTracedHook"
    assert HealthCheckRunHook.__name__ == "HealthCheckRunHook"
    assert (
        lexigram.ai.observability.AIObservabilityStartedHook
        is AIObservabilityStartedHook
    )
    assert lexigram.ai.observability.LLMCallTracedHook is LLMCallTracedHook
    assert lexigram.ai.observability.HealthCheckRunHook is HealthCheckRunHook


def test_observability_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.observability.hooks import (
        AIObservabilityStartedHook,
        HealthCheckRunHook,
        LLMCallTracedHook,
    )

    started = AIObservabilityStartedHook()
    traced = LLMCallTracedHook(provider="openai", model="gpt-4o")
    checked = HealthCheckRunHook(component="llm", healthy=True)

    assert is_dataclass(started)
    assert is_dataclass(traced)
    assert is_dataclass(checked)

    with pytest.raises(TypeError):
        LLMCallTracedHook("openai", "gpt-4o")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        traced.provider = "anthropic"  # type: ignore[misc]

    with pytest.raises(TypeError):
        AIObservabilityStartedHook("unexpected")  # type: ignore[misc]

    with pytest.raises(TypeError):
        HealthCheckRunHook("llm", True)  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        checked.component = "rag"  # type: ignore[misc]
