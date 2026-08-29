"""Web + Cache + SQL cache-aside pattern scenario.

Packages under test: lexigram-web, lexigram-cache, lexigram-sql
Infrastructure: in-memory SQLite + in-memory cache (no live service required)

Scenario:
1. Boot a minimal application with WebModule + CacheModule + DatabaseModule.
2. GET  /api/v1/items/{id}  (cold)  -> DB hit, response cached.
3. GET  /api/v1/items/{id}  (warm)  -> Cache hit, DB not queried.
4. PUT  /api/v1/items/{id}          -> Item updated, cache entry invalidated.
5. GET  /api/v1/items/{id}  (cold)  -> DB hit again after invalidation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_cache_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> "ScenarioTestBed":
    """Boot a minimal Web + Cache + SQL test application."""
    async with scenario_bed(create_cache_app) as scenario:
        yield scenario


class TestWebCacheSql:
    """Web + Cache + SQL cache-aside read-through and invalidation."""

    async def test_first_request_hits_database(self, bed: "ScenarioTestBed") -> None:
        """The first GET for an item queries the database and populates the cache."""
        resp = await bed.client.post("/api/v1/items", json={"name": "cached-item"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.get(f"/api/v1/items/{item_id}")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "MISS"
        assert resp.json()["name"] == "cached-item"

    async def test_second_request_hits_cache(self, bed: "ScenarioTestBed") -> None:
        """The second GET for the same item is served entirely from the cache."""
        resp = await bed.client.post("/api/v1/items", json={"name": "cached-item-2"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        await bed.client.get(f"/api/v1/items/{item_id}")

        resp = await bed.client.get(f"/api/v1/items/{item_id}")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "HIT"

    async def test_update_invalidates_cache(self, bed: "ScenarioTestBed") -> None:
        """Updating an item evicts the stale cache entry."""
        resp = await bed.client.post("/api/v1/items", json={"name": "stale-item"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        await bed.client.get(f"/api/v1/items/{item_id}")
        await bed.client.get(f"/api/v1/items/{item_id}")  # HIT

        put = await bed.client.put(
            f"/api/v1/items/{item_id}", json={"name": "fresh-item"}
        )
        assert put.status_code == 200

        resp = await bed.client.get(f"/api/v1/items/{item_id}")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "MISS"
        assert resp.json()["name"] == "fresh-item"
