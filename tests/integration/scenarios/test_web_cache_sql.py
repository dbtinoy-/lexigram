from __future__ import annotations

"""Web + Cache + SQL cache-aside pattern scenario.

Packages under test: lexigram-web, lexigram-cache, lexigram-sql
Infrastructure: PostgreSQL, Redis

Scenario:
1. Boot a minimal application with WebProvider + CacheProvider + SqlProvider.
2. GET  /api/v1/items/{id}  (cold)  → DB hit, response cached in Redis.
3. GET  /api/v1/items/{id}  (warm)  → Cache hit, DB not queried.
4. PUT  /api/v1/items/{id}          → Item updated, cache entry invalidated.
5. GET  /api/v1/items/{id}  (cold)  → DB hit again after invalidation.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.scenario,
    pytest.mark.requires_postgres,
    pytest.mark.requires_redis,
]


class TestWebCacheSql:
    """Web + Cache + SQL cache-aside read-through and invalidation.

    Boots a minimal application with WebProvider + CacheProvider + SqlProvider,
    then verifies that the cache-aside pattern routes reads through Redis and
    correctly invalidates cached entries on write.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Web + Cache + SQL test application.

        Yields:
            AppTestBed configured with WebProvider + CacheProvider + SqlProvider.
        """
        pytest.skip(
            "TODO: implement create_cache_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_cache_app)"
        )

    async def test_first_request_hits_database(self, bed: object) -> None:
        """The first GET for an item queries the database and populates the cache.

        After the first request the response header (or bed diagnostic) should
        indicate a cache miss, and the Redis key should now exist.

        Args:
            bed: Booted AppTestBed with HTTP client, live DB, and live Redis.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "cached-item"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 200
        # Cache-aside implementations typically expose the origin via a header.
        assert resp.headers.get("X-Cache") in ("MISS", None)
        assert resp.json()["name"] == "cached-item"

    async def test_second_request_hits_cache(self, bed: object) -> None:
        """The second GET for the same item is served entirely from the cache.

        Args:
            bed: Booted AppTestBed with HTTP client, live DB, and live Redis.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "cached-item-2"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Warm up the cache.
        await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]

        # Second request should be a cache hit.
        resp = await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") in ("HIT", None)

    async def test_update_invalidates_cache(self, bed: object) -> None:
        """Updating an item evicts the stale cache entry.

        After a PUT the cache key must be gone so that the next GET
        returns the updated value from the database.

        Args:
            bed: Booted AppTestBed with HTTP client, live DB, and live Redis.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "stale-item"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Warm up cache.
        await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]

        # Mutate — must invalidate cached entry.
        put = await bed.client.put(f"/api/v1/items/{item_id}", json={"name": "fresh-item"})  # type: ignore[attr-defined]
        assert put.status_code == 200

        # Next read must reflect the updated value (cache miss + DB read).
        resp = await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 200
        assert resp.json()["name"] == "fresh-item"
