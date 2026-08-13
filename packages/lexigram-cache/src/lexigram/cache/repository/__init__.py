"""
RepositoryProtocol pattern implementations for Lexigram Cache.

This package provides repository patterns that offer domain-specific
caching abstractions on top of the core cache service.
"""

from __future__ import annotations

from lexigram.cache.repository.base import (
    CacheRepository,
    CollectionRepository,
    ConfigurationRepository,
    EntityRepository,
    QueryRepository,
)

__all__ = [
    "CacheRepository",
    "CollectionRepository",
    "ConfigurationRepository",
    "EntityRepository",
    "QueryRepository",
]
