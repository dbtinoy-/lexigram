"""Data caching layer — local implementations removed.

All caching is now provided by ``lexigram-cache``.  Inject
``CacheBackendProtocol`` from ``lexigram.contracts.infra.cache`` into data
sources that need caching, and use ``MemoryCacheBackend`` from
``lexigram.cache`` as the in-process backend.
"""

from __future__ import annotations
