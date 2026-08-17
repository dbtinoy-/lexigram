"""DI decorators and lifecycle management for lexigram-admin.

This module provides decorator integration with lexigram's DI system,
including @singleton, @scoped, and @transient decorators.

FWK-02: Apply lifecycle decorators to services.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, Self, TypeVar

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Try importing from lexigram
# ============================================================================

try:
    from lexigram.di.decorators import scoped as lexigram_scoped
    from lexigram.di.decorators import singleton as lexigram_singleton
    from lexigram.di.decorators import transient as lexigram_transient

    HAS_LEX_DI = True
except ImportError:
    HAS_LEX_DI = False
    lexigram_singleton = None  # type: ignore[assignment]
    lexigram_scoped = None  # type: ignore[assignment]
    lexigram_transient = None  # type: ignore[assignment]


# ============================================================================
# Lifecycle Scope
# ============================================================================


class Scope(str, Enum):
    """Service lifecycle scopes."""

    SINGLETON = "singleton"  # One instance per container
    SCOPED = "scoped"  # One instance per scope (request)
    TRANSIENT = "transient"  # New instance each time


# ============================================================================
# Fallback Decorators
# ============================================================================

_singletons: dict[type, Any] = {}


def _fallback_singleton(cls: type[T]) -> type[T]:
    """Fallback singleton decorator using class-level caching."""

    def new_method(cls_inner: type[T], *args: Any, **kwargs: Any) -> T:
        if cls_inner not in _singletons:
            instance = object.__new__(cls_inner)
            _singletons[cls_inner] = instance
        return _singletons[cls_inner]

    cls.__new__ = new_method  # type: ignore[method-assign,assignment]
    return cls


def _fallback_scoped(cls: type[T]) -> type[T]:
    """Fallback scoped decorator (acts like transient without request context)."""
    # Without lexigram's context system, scoped behaves like transient
    return cls


def _fallback_transient(cls: type[T]) -> type[T]:
    """Fallback transient decorator (no-op)."""
    return cls


# ============================================================================
# Public Decorators
# ============================================================================


def singleton(cls: type[T]) -> type[T]:
    """Mark a class as singleton (one instance per container).

    Example:
        >>> @singleton
        ... class ConfigService:
        ...     def __init__(self):
        ...         self.settings = load_settings()
    """
    if HAS_LEX_DI and lexigram_singleton:  # type: ignore[truthy-function]
        return lexigram_singleton(cls)
    return _fallback_singleton(cls)


def scoped(cls: type[T]) -> type[T]:
    """Mark a class as scoped (one instance per request).

    Example:
        >>> @scoped
        ... class RequestContext:
        ...     def __init__(self, request):
        ...         self.user = request.user
    """
    if HAS_LEX_DI and lexigram_scoped:  # type: ignore[truthy-function]
        return lexigram_scoped(cls)
    return _fallback_scoped(cls)


def transient(cls: type[T]) -> type[T]:
    """Mark a class as transient (new instance each time).

    Example:
        >>> @transient
        ... class QueryBuilder:
        ...     def __init__(self):
        ...         self.conditions = []
    """
    if HAS_LEX_DI and lexigram_transient:  # type: ignore[truthy-function]
        return lexigram_transient(cls)
    return _fallback_transient(cls)


# ============================================================================
# Injectable Decorator
# ============================================================================


def injectable(
    scope: Scope = Scope.TRANSIENT,
    token: str | None = None,
) -> Callable[[type[T]], type[T]]:
    """Mark a class as injectable with specified scope.

    Args:
        scope: Lifecycle scope (singleton, scoped, transient)
        token: Optional token for registration

    Example:
        >>> @injectable(scope=Scope.SINGLETON)
        ... class DatabaseConnection:
        ...     pass
    """

    def decorator(cls: type[T]) -> type[T]:
        # Apply appropriate scope decorator
        if scope == Scope.SINGLETON:
            decorated = singleton(cls)
        elif scope == Scope.SCOPED:
            decorated = scoped(cls)
        else:
            decorated = transient(cls)

        # Store metadata
        decorated.__injectable_scope__ = scope  # type: ignore[attr-defined]
        decorated.__injectable_token__ = token  # type: ignore[attr-defined]

        return decorated

    return decorator


# ============================================================================
# Context Manager for Scopes
# ============================================================================


class ScopeContext:
    """Context manager for managing scoped instances.

    Example:
        >>> async with ScopeContext() as ctx:
        ...     service = ctx.resolve(RequestScopedService)
        ...     # Service is scoped to this context
    """

    def __init__(self) -> None:
        self._instances: dict[type, Any] = {}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self._instances.clear()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        # Cleanup async resources
        for instance in self._instances.values():
            if hasattr(instance, "close") and callable(instance.close):
                close = instance.close
                if callable(close):
                    result = close()
                    if hasattr(result, "__await__"):
                        await result
        self._instances.clear()

    def resolve(self, cls: type[T], *args: Any, **kwargs: Any) -> T:
        """Resolve an instance within this scope."""
        scope = getattr(cls, "__injectable_scope__", Scope.TRANSIENT)

        if scope == Scope.SINGLETON:
            # Use global singleton
            if cls not in _singletons:
                _singletons[cls] = cls(*args, **kwargs)
            return _singletons[cls]

        if scope == Scope.SCOPED:
            # Use scope-local instance
            if cls not in self._instances:
                self._instances[cls] = cls(*args, **kwargs)
            return self._instances[cls]

        # Transient - new instance
        return cls(*args, **kwargs)


# ============================================================================
# Clear Singletons (for testing)
# ============================================================================


def clear_singletons() -> None:
    """Clear all singleton instances (useful for testing)."""
    _singletons.clear()


__all__ = [
    # Flags
    "HAS_LEX_DI",
    # Scope enum
    "Scope",
    # Context
    "ScopeContext",
    # Utils
    "clear_singletons",
    "injectable",
    "scoped",
    # Decorators
    "singleton",
    "transient",
]
