"""
Service layer for Lexigram Cache.

This module provides high-level caching services including
the main CacheService, decorators, and protection mechanisms.
"""

from __future__ import annotations

from lexigram.cache.service.core import CacheService
from lexigram.cache.service.decorators import (
    CacheDecorator,
    cache,
    conditional_cache,
    invalidate_cache,
    remember,
)

__all__ = [
    "CacheDecorator",
    # Core service
    "CacheService",
    # Decorators
    "cache",
    "conditional_cache",
    "invalidate_cache",
    "remember",
]
