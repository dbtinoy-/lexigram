"""Tests for SessionStoreRegistry."""

from __future__ import annotations

from lexigram.ai.session.stores.cache import CacheSessionStore
from lexigram.ai.session.stores.database import DatabaseSessionStore
from lexigram.ai.session.stores.in_memory import InMemorySessionStore
from lexigram.ai.session.stores.registry import SessionStoreRegistry


def test_registry_has_all_default_backends() -> None:
    """with_defaults registers in_memory, cache, and database."""
    registry = SessionStoreRegistry.with_defaults()
    assert set(registry.backends()) == {"in_memory", "cache", "database"}


def test_create_in_memory_returns_instance_binding() -> None:
    """in_memory binds an eager instance (no DI dependencies)."""
    binding = SessionStoreRegistry.with_defaults().create_store("in_memory")
    assert binding.as_factory is False
    assert isinstance(binding.store, InMemorySessionStore)


def test_create_cache_returns_factory_binding() -> None:
    """cache binds a lazy factory so the container injects the cache backend."""
    binding = SessionStoreRegistry.with_defaults().create_store("cache")
    assert binding.as_factory is True
    assert binding.store is CacheSessionStore


def test_create_database_returns_factory_binding() -> None:
    """database binds a lazy factory so the container injects the db provider."""
    binding = SessionStoreRegistry.with_defaults().create_store("database")
    assert binding.as_factory is True
    assert binding.store is DatabaseSessionStore


def test_create_unknown_falls_back_to_in_memory() -> None:
    """An unknown backend falls back to the in_memory instance binding."""
    binding = SessionStoreRegistry.with_defaults().create_store("bogus")
    assert binding.as_factory is False
    assert isinstance(binding.store, InMemorySessionStore)
