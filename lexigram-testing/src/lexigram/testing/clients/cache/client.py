"""Cache testing client module.

This module re-exports testing components for backward compatibility.
"""

from __future__ import annotations

from lexigram.testing.clients.cache.bed import CacheTestBed
from lexigram.testing.clients.cache.client_core import CacheTestClient
from lexigram.testing.clients.cache.data import CacheTestData

__all__ = [
    "CacheTestBed",
    "CacheTestClient",
    "CacheTestData",
]
