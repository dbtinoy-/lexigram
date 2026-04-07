"""Service factory helpers for provider initialization.

Separate service creation so the provider contains higher-level orchestration only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.cache.protocols import CacheBackendProtocol
    from lexigram.cache.service.core import CacheService
    from lexigram.cache.service.stampede import StampedeProtectedCache


def create_service(
    provider: Any,
    backend_name: str,
    backend: CacheBackendProtocol,
    protection: StampedeProtectedCache | None,
) -> CacheService:
    """Create and return a CacheService instance for a backend.

    Currently the service is a thin wrapper around the core `CacheService`.
    Keeping this factory isolated makes it easier to add per-backend customization later.
    """
    from lexigram.cache.service.core import CacheService

    return CacheService(provider=provider, protection=protection)


__all__ = ["create_service"]
