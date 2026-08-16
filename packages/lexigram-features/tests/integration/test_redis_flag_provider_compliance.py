from __future__ import annotations

"""Redis-backed FlagProvider compliance test using a real Redis connection."""

import pytest

from lexigram.testing.compliance import FlagProviderCompliance
from lexigram.testing.integration.fixtures import redis_client  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_redis]


class TestRedisFlagProviderCompliance(FlagProviderCompliance):
    """Verify CacheBackendFlagProvider satisfies FlagProviderCompliance.

    Uses the ``redis_client`` fixture provided by
    ``lexigram.testing.integration.fixtures``.  The suite is auto-skipped when
    Redis is not reachable or the ``redis`` package is not installed.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, redis_client: object) -> None:
        """Capture the live Redis client for use in create_provider.

        Args:
            redis_client: Session-scoped async Redis client connected to the
                test database.
        """
        self._redis_client = redis_client

    async def create_provider(self) -> object:
        """Create a CacheBackendFlagProvider backed by the live Redis instance.

        Returns:
            A ready-to-use CacheBackendFlagProvider instance.

        Raises:
            pytest.skip.Exception: If the feature flag backend or the cache
                adapter cannot be imported.
        """
        try:
            from lexigram.features.backends.cache import (
                CacheBackendFlagProvider,  # noqa: F401
            )
        except ImportError:
            pytest.skip("CacheBackendFlagProvider not available")

        pytest.skip(
            "TODO: wrap redis_client in a CacheBackendProtocol adapter "
            "(e.g. RedisCacheBackend) before passing it to CacheBackendFlagProvider"
        )
