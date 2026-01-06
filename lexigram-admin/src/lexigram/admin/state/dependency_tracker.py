"""Dependency Tracking Service for Reactive Updates."""

from __future__ import annotations

from typing import Any


class DependencyStack:
    """Manages the stack of currently computing properties."""

    def __init__(self) -> None:
        self._stack: list[str] = []

    def push(self, key: str) -> None:
        """Push a computed property key onto the running stack."""
        self._stack.append(key)

    def pop(self) -> str | None:
        """Pop the current computed property key."""
        if self._stack:
            return self._stack.pop()
        return None

    @property
    def current(self) -> str | None:
        """Get the currently executing computed property key."""
        if self._stack:
            return self._stack[-1]
        return None


class DependencyTracker:
    """Tracks dependencies between computed properties for reactive updates."""

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        # Maps computed property key -> set of source keys it depends on (Computed -> {Sources})
        # This is primarily for debugging/introspection if needed, but invalidation relies on Source -> {Computeds}
        # Actually, for efficient invalidation we need Source -> {Computeds}.

        # Source Key -> Set of Subscriber Keys (Who depends on me?)
        self._subscribers: dict[str, set[str]] = {}

        # Computed Key -> Cached Value
        self._cache: dict[str, Any] = {}

        # The stack of currently running computations
        self.stack = DependencyStack()

        self._initialized = True

    def track(self, source_key: str) -> None:
        """Record that the currently running computation depends on this source.

        Called by Signals when they are read.
        """
        current_computation = self.stack.current
        if current_computation:
            # The current computation depends on source_key
            if source_key not in self._subscribers:
                self._subscribers[source_key] = set()
            self._subscribers[source_key].add(current_computation)

    def trigger(self, source_key: str) -> None:
        """Trigger invalidation for all dependants of this source.

        Called by Signals when they change.
        """
        if source_key in self._subscribers:
            dependants = self._subscribers[source_key]
            # Copy to avoid modification while iterating (though we just invalidate cache)
            to_invalidate = list(dependants)

            for computed_key in to_invalidate:
                self.invalidate(computed_key)

    def invalidate(self, key: str) -> None:
        """Invalidate a specific key from cache."""
        if key in self._cache:
            del self._cache[key]

        # If this computed property is also a source for others, trigger them too!
        # (Propagation of invalidation)
        self.trigger(key)

    def get_cached(self, key: str) -> Any:
        return self._cache.get(key)

    def set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def has_cache(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        """Clear all state (testing mostly)."""
        self._subscribers.clear()
        self._cache.clear()


async def get_dependency_tracker() -> DependencyTracker:
    """Get the global dependency tracker instance."""
    from lexigram.admin.lib.di import (  # type: ignore[attr-defined]
        get_admin_container,
    )

    container = get_admin_container()
    return await container.resolve(DependencyTracker)


def __getattr__(name: str) -> Any:
    if name == "dependency_tracker":
        raise AttributeError(
            "dependency_tracker is now async. Use: await get_dependency_tracker()",
        )
    raise AttributeError(f"module {__name__} has no attribute {name}")
