"""Session store registry — registry-based dispatch of session stores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.ai.session.stores.cache import CacheSessionStore
from lexigram.ai.session.stores.database import DatabaseSessionStore
from lexigram.ai.session.stores.in_memory import InMemorySessionStore


@dataclass(frozen=True)
class SessionStoreBinding:
    """A resolved store binding for the DI container.

    Attributes:
        backend: The backend name that produced this binding.
        store: A store instance (when ``as_factory`` is False) or a store
            class (when ``as_factory`` is True).
        as_factory: Whether to bind the store as a DI factory. In-memory has
            no dependencies so it is bound eagerly as an instance; cache and
            database require DI-injected backends so they are bound lazily as
            factories.
    """

    backend: str
    store: Any
    as_factory: bool


class SessionStoreRegistry:
    """Registry of session-store bindings, keyed by backend name.

    Resolves a backend name to a :class:`SessionStoreBinding` describing how
    to register the store in the DI container. Unknown backends fall back to
    the in-memory binding, matching the historical provider behavior.

    Usage::

        registry = SessionStoreRegistry.with_defaults()
        binding = registry.create_store("cache")
        if binding.as_factory:
            container.singleton(SessionStoreProtocol, factory=binding.store)
        else:
            container.singleton(SessionStoreProtocol, instance=binding.store)
    """

    def __init__(self) -> None:
        """Initialise an empty store registry."""
        self._bindings: dict[str, SessionStoreBinding] = {}

    @classmethod
    def with_defaults(cls) -> SessionStoreRegistry:
        """Return a registry populated with the built-in session stores.

        Returns:
            A :class:`SessionStoreRegistry` pre-registered for in_memory,
            cache, and database. ``in_memory`` binds an eager instance;
            ``cache`` and ``database`` bind lazy factories.
        """
        registry = cls()
        registry.register(
            "in_memory",
            SessionStoreBinding("in_memory", InMemorySessionStore(), as_factory=False),
        )
        registry.register(
            "cache",
            SessionStoreBinding("cache", CacheSessionStore, as_factory=True),
        )
        registry.register(
            "database",
            SessionStoreBinding("database", DatabaseSessionStore, as_factory=True),
        )
        return registry

    def register(self, backend: str, binding: SessionStoreBinding) -> None:
        """Register a binding under a backend name.

        Args:
            backend: Backend name (e.g. ``"cache"``).
            binding: The binding to register under *backend*.
        """
        self._bindings[backend] = binding

    def create_store(self, backend: str) -> SessionStoreBinding:
        """Resolve a store binding by backend name.

        Args:
            backend: Backend name to dispatch on.

        Returns:
            The resolved store binding, falling back to the in-memory binding
            for unknown backends.
        """
        binding = self._bindings.get(backend)
        if binding is None:
            return self._bindings["in_memory"]
        return binding

    def backends(self) -> list[str]:
        """Return the registered backend names.

        Returns:
            List of backend names in registration order.
        """
        return list(self._bindings.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._bindings


__all__ = ["SessionStoreBinding", "SessionStoreRegistry"]
