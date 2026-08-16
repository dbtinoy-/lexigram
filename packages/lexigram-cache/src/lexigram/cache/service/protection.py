"""
Cache stampede protection for Lexigram Framework.

This module implements cache stampede protection using distributed locking
to prevent thundering herd problems when cache keys expire simultaneously.
"""

from __future__ import annotations

from lexigram.cache.service.stampede import CacheEntry, StampedeProtectedCache

__all__ = ["CacheEntry", "StampedeProtectedCache"]
