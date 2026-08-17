"""Feedback loop module for continuous learning."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("lexigram-ai-safety")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from lexigram.ai.feedback.config import FeedbackConfig
    from lexigram.ai.feedback.di.provider import FeedbackProvider
    from lexigram.ai.feedback.exceptions import (
        FeedbackAuthorizationError,
        FeedbackError,
        FeedbackProcessingError,
        FeedbackTooLargeError,
        FeedbackValidationError,
    )
    from lexigram.ai.feedback.hooks import (
        FeedbackProcessedHook,
        FeedbackStoredHook,
        FeedbackSubmittedHook,
    )
    from lexigram.ai.feedback.middleware import (
        FeedbackContext,
        FeedbackMiddleware,
    )
    from lexigram.ai.feedback.module import FeedbackModule
    from lexigram.ai.feedback.services.collector import FeedbackCollector
    from lexigram.ai.feedback.services.feedback_service import FeedbackService
    from lexigram.ai.feedback.storage import (
        CachedFeedbackStore,
        DatabaseFeedbackStore,
        FeedbackStoreProtocol,
        FeedbackSummary,
    )
    from lexigram.ai.feedback.types import FeedbackItem, FeedbackType

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Config ---
    "FeedbackConfig": ("lexigram.ai.feedback.config", "FeedbackConfig"),
    # --- DI ---
    "FeedbackProvider": ("lexigram.ai.feedback.di.provider", "FeedbackProvider"),
    "FeedbackModule": ("lexigram.ai.feedback.module", "FeedbackModule"),
    # --- Exceptions ---
    "FeedbackAuthorizationError": (
        "lexigram.ai.feedback.exceptions",
        "FeedbackAuthorizationError",
    ),
    "FeedbackError": ("lexigram.ai.feedback.exceptions", "FeedbackError"),
    "FeedbackProcessingError": (
        "lexigram.ai.feedback.exceptions",
        "FeedbackProcessingError",
    ),
    "FeedbackTooLargeError": (
        "lexigram.ai.feedback.exceptions",
        "FeedbackTooLargeError",
    ),
    "FeedbackValidationError": (
        "lexigram.ai.feedback.exceptions",
        "FeedbackValidationError",
    ),
    # --- Hooks ---
    "FeedbackProcessedHook": (
        "lexigram.ai.feedback.hooks",
        "FeedbackProcessedHook",
    ),
    "FeedbackStoredHook": ("lexigram.ai.feedback.hooks", "FeedbackStoredHook"),
    "FeedbackSubmittedHook": ("lexigram.ai.feedback.hooks", "FeedbackSubmittedHook"),
    # --- Middleware ---
    "FeedbackContext": ("lexigram.ai.feedback.middleware", "FeedbackContext"),
    "FeedbackMiddleware": ("lexigram.ai.feedback.middleware", "FeedbackMiddleware"),
    # --- Services ---
    "FeedbackCollector": (
        "lexigram.ai.feedback.services.collector",
        "FeedbackCollector",
    ),
    "FeedbackService": (
        "lexigram.ai.feedback.services.feedback_service",
        "FeedbackService",
    ),
    # --- Storage ---
    "CachedFeedbackStore": ("lexigram.ai.feedback.storage", "CachedFeedbackStore"),
    "DatabaseFeedbackStore": ("lexigram.ai.feedback.storage", "DatabaseFeedbackStore"),
    "FeedbackSummary": ("lexigram.ai.feedback.storage", "FeedbackSummary"),
    # --- Types ---
    "FeedbackItem": ("lexigram.ai.feedback.types", "FeedbackItem"),
    "FeedbackType": ("lexigram.ai.feedback.types", "FeedbackType"),
    # --- Protocols ---
    "FeedbackProtocol": ("lexigram.ai.feedback.protocols", "FeedbackProtocol"),
    "FeedbackStoreProtocol": (
        "lexigram.ai.feedback.protocols",
        "FeedbackStoreProtocol",
    ),
    # --- Events ---
    "FeedbackSubmittedEvent": ("lexigram.ai.feedback.events", "FeedbackSubmittedEvent"),
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
    "CachedFeedbackStore",
    "DatabaseFeedbackStore",
    "FeedbackAuthorizationError",
    "FeedbackCollector",
    "FeedbackConfig",
    "FeedbackContext",
    "FeedbackError",
    "FeedbackItem",
    "FeedbackMiddleware",
    "FeedbackModule",
    "FeedbackProcessedHook",
    "FeedbackProcessingError",
    "FeedbackProtocol",
    "FeedbackProvider",
    "FeedbackService",
    "FeedbackStoreProtocol",
    "FeedbackStoredHook",
    "FeedbackSubmittedEvent",
    "FeedbackSubmittedHook",
    "FeedbackSummary",
    "FeedbackTooLargeError",
    "FeedbackType",
    "FeedbackValidationError",
]
