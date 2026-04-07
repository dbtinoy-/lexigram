"""Intelligence monitoring and observability.

This module provides tools for monitoring the health, performance,
and behavior of the intelligence layer.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("lexigram-ai-observability")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    from lexigram.ai.observability.config import ObservabilityConfig
    from lexigram.ai.observability.decorators import (
        trace_llm,
        trace_rag,
        trace_vector,
        track_embedding_operation,
        track_llm_call,
        track_vector_operation,
    )
    from lexigram.ai.observability.di.provider import ObservabilityProvider
    from lexigram.ai.observability.exceptions import (
        HealthCheckError,
        MetricsError,
        ObservabilityError,
        TracingError,
    )
    from lexigram.ai.observability.health import AIHealthMonitor
    from lexigram.ai.observability.hooks import (
        AIObservabilityStartedHook,
        HealthCheckRunHook,
        LLMCallTracedHook,
    )
    from lexigram.ai.observability.metrics import (
        AIMetrics,
    )
    from lexigram.ai.observability.module import ObservabilityModule
    from lexigram.ai.observability.protocols import (
        AIHealthMonitorProtocol,
        AIMetricsProtocol,
        AITracerProtocol,
        ObservabilityProtocol,
    )
    from lexigram.ai.observability.tracing import (
        AITracer,
    )
    from lexigram.ai.observability.wrappers import (
        ObservableLLMClient,
        ObservableVectorStore,
    )
    from lexigram.contracts import HealthCheckResult, HealthStatus

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Callback ---
    "CallbackManagerImpl": (
        "lexigram.ai.observability.callback_manager",
        "CallbackManagerImpl",
    ),
    # --- Hooks ---
    "AIObservabilityStartedHook": (
        "lexigram.ai.observability.hooks",
        "AIObservabilityStartedHook",
    ),
    "HealthCheckRunHook": (
        "lexigram.ai.observability.hooks",
        "HealthCheckRunHook",
    ),
    "LLMCallTracedHook": (
        "lexigram.ai.observability.hooks",
        "LLMCallTracedHook",
    ),
    # --- Config ---
    "ObservabilityConfig": ("lexigram.ai.observability.config", "ObservabilityConfig"),
    # --- DI ---
    "ObservabilityProvider": (
        "lexigram.ai.observability.di.provider",
        "ObservabilityProvider",
    ),
    "ObservabilityModule": ("lexigram.ai.observability.module", "ObservabilityModule"),
    # --- Exceptions ---
    "ObservabilityError": (
        "lexigram.ai.observability.exceptions",
        "ObservabilityError",
    ),
    "HealthCheckError": ("lexigram.ai.observability.exceptions", "HealthCheckError"),
    "MetricsError": ("lexigram.ai.observability.exceptions", "MetricsError"),
    "TracingError": ("lexigram.ai.observability.exceptions", "TracingError"),
    # --- Health ---
    "AIHealthMonitor": ("lexigram.ai.observability.health", "AIHealthMonitor"),
    # --- Metrics ---
    "AIMetrics": ("lexigram.ai.observability.metrics", "AIMetrics"),
    "track_llm_call": ("lexigram.ai.observability.decorators", "track_llm_call"),
    "track_vector_operation": (
        "lexigram.ai.observability.decorators",
        "track_vector_operation",
    ),
    "track_embedding_operation": (
        "lexigram.ai.observability.decorators",
        "track_embedding_operation",
    ),
    # --- Protocols ---
    "ObservabilityProtocol": (
        "lexigram.ai.observability.protocols",
        "ObservabilityProtocol",
    ),
    "AITracerProtocol": ("lexigram.ai.observability.protocols", "AITracerProtocol"),
    "AIMetricsProtocol": ("lexigram.ai.observability.protocols", "AIMetricsProtocol"),
    "AIHealthMonitorProtocol": (
        "lexigram.ai.observability.protocols",
        "AIHealthMonitorProtocol",
    ),
    # --- Tracing ---
    "AITracer": ("lexigram.ai.observability.tracing", "AITracer"),
    "trace_llm": ("lexigram.ai.observability.decorators", "trace_llm"),
    "trace_rag": ("lexigram.ai.observability.decorators", "trace_rag"),
    "trace_vector": ("lexigram.ai.observability.decorators", "trace_vector"),
    # --- Wrappers ---
    "ObservableLLMClient": (
        "lexigram.ai.observability.wrappers",
        "ObservableLLMClient",
    ),
    "ObservableVectorStore": (
        "lexigram.ai.observability.wrappers",
        "ObservableVectorStore",
    ),
    # --- Contracts Re-exports ---
    "HealthCheckResult": ("lexigram.contracts", "HealthCheckResult"),
    "HealthStatus": ("lexigram.contracts", "HealthStatus"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AIHealthMonitor",
    "AIHealthMonitorProtocol",
    "AIMetrics",
    "AIMetricsProtocol",
    "AIObservabilityStartedHook",
    "AITracer",
    "AITracerProtocol",
    "CallbackManagerImpl",
    "HealthCheckError",
    "HealthCheckResult",
    "HealthCheckRunHook",
    "HealthStatus",
    "LLMCallTracedHook",
    "MetricsError",
    "ObservabilityConfig",
    "ObservabilityError",
    "ObservabilityModule",
    "ObservabilityProtocol",
    "ObservabilityProvider",
    "ObservableLLMClient",
    "ObservableVectorStore",
    "TracingError",
    "trace_llm",
    "trace_rag",
    "trace_vector",
    "track_embedding_operation",
    "track_llm_call",
    "track_vector_operation",
]
