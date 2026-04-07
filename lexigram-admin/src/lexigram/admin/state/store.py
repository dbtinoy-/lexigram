"""Reactive state management based on Signals for Lexigram Admin."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

# Context for tracking active computations
_active_effect: contextvars.ContextVar[Effect | None] = contextvars.ContextVar(
    "_active_effect",
    default=None,
)


class Signal(Generic[T]):
    """A reactive value that can be observed/subscribed to."""

    def __init__(self, value: T) -> None:
        self._value = value
        self._subscribers: set[Effect | Computed] = set()

    def get(self) -> T:
        """Get the value and track the dependency if an effect is active."""
        effect = _active_effect.get()
        if effect:
            self._subscribers.add(effect)
            effect.add_dependency(self)
        return self._value

    def set(self, value: T) -> None:
        """Update the value and notify all subscribers."""
        if self._value == value:
            return
        self._value = value
        # Copy subscribers to avoid modification during iteration
        for subscriber in list(self._subscribers):
            subscriber.update()

    def add_subscriber(self, subscriber: Effect | Computed) -> None:
        """Add a subscriber to this signal."""
        self._subscribers.add(subscriber)

    def remove_subscriber(self, subscriber: Effect | Computed) -> None:
        """Remove a subscriber from this signal."""
        self._subscribers.discard(subscriber)

    def __repr__(self) -> str:
        return f"Signal({self._value})"


class Computed(Generic[T]):
    """A value derived from other signals or computed values."""

    def __init__(self, fn: Callable[[], T]) -> None:
        self._fn = fn
        self._value: T | None = None
        self._dirty = True
        self._subscribers: set[Effect | Computed] = set()
        self._dependencies: set[Signal | Computed] = set()

    def get(self) -> T:
        """Get the computed value, re-evaluating if dirty."""
        effect = _active_effect.get()
        if effect:
            self._subscribers.add(effect)
            effect.add_dependency(self)

        if self._dirty:
            self._evaluate()
        return self._value  # type: ignore[return-value]

    def _evaluate(self) -> None:
        """Run the computation and track dependencies."""
        # Unsubscribe from old dependencies
        for dep in self._dependencies:
            dep.remove_subscriber(self)
        self._dependencies.clear()

        # Run with tracking
        token = _active_effect.set(self)  # type: ignore[arg-type]
        try:
            self._value = self._fn()
        finally:
            _active_effect.reset(token)

        self._dirty = False

    def update(self) -> None:
        """Mark as dirty and notify subscribers."""
        if not self._dirty:
            self._dirty = True
            for subscriber in list(self._subscribers):
                subscriber.update()

    def add_dependency(self, dependency: Signal | Computed) -> None:
        """Add a dependency to this computed value."""
        self._dependencies.add(dependency)

    def remove_subscriber(self, subscriber: Effect | Computed) -> None:
        """Remove a subscriber from this computed value."""
        self._subscribers.discard(subscriber)

    def __repr__(self) -> str:
        return f"Computed({self._value})"


class Effect:
    """A side-effect that runs whenever its dependencies change."""

    def __init__(self, fn: Callable[[], None]) -> None:
        self._fn = fn
        self._dependencies: set[Signal | Computed] = set()
        self._run()

    def _run(self) -> None:
        """Run the effect and track dependencies."""
        # Unsubscribe from old dependencies
        for dep in self._dependencies:
            dep.remove_subscriber(self)
        self._dependencies.clear()

        # Run with tracking
        token = _active_effect.set(self)
        try:
            self._fn()
        finally:
            _active_effect.reset(token)

    def update(self) -> None:
        """Re-run the effect because a dependency changed."""
        self._run()

    def add_dependency(self, dependency: Signal | Computed) -> None:
        """Add a dependency to this effect."""
        self._dependencies.add(dependency)


def signal(value: T) -> Signal[T]:
    """Helper to create a signal."""
    return Signal(value)


def computed(fn: Callable[[], T]) -> Computed[T]:
    """Helper to create a computed value."""
    return Computed(fn)


def watch(fn: Callable[[], None]) -> Effect:
    """Helper to create an effect (watcher)."""
    return Effect(fn)


class GlobalStore:
    """Base class for global state containers."""
