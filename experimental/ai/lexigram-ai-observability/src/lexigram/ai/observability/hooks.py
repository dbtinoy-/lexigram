"""Root hook payload surface for lexigram-ai-observability.

Defines canonical payload dataclasses for AI observability lifecycle hook
points. Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AIObservabilityStartedHook",
    "HealthCheckRunHook",
    "LLMCallTracedHook",
]


@dataclass(frozen=True, kw_only=True)
class AIObservabilityStartedHook:
    """Payload fired after the AI observability subsystem has initialised."""


@dataclass(frozen=True, kw_only=True)
class LLMCallTracedHook:
    """Payload fired when a completed LLM call is recorded by the tracer.

    Attributes:
        provider: Provider identifier whose call was traced (e.g. ``"openai"``).
        model: Model name that was traced (e.g. ``"gpt-4o"``).
    """

    provider: str
    model: str


@dataclass(frozen=True, kw_only=True)
class HealthCheckRunHook:
    """Payload fired after an AI health check completes.

    Attributes:
        component: Name of the component that was checked (e.g. ``"llm"``).
        healthy: ``True`` if the component reported a healthy state.
    """

    component: str
    healthy: bool
