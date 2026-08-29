"""Web + SQL full CRUD lifecycle scenario.

Packages under test: lexigram-web, lexigram-sql
Infrastructure: in-memory SQLite (no live service required)

Scenario:
1. Boot a minimal application with WebProvider + SqlProvider.
2. POST  /api/v1/items          → 201 Created  (create)
3. GET   /api/v1/items/{id}     → 200 OK       (read)
4. PUT   /api/v1/items/{id}     → 200 OK       (update)
5. DELETE /api/v1/items/{id}    → 204 No Content (delete)
6. GET   /api/v1/items/{id}     → 404 Not Found  (verify delete)
7. GET   /api/v1/items?page=1&size=10 → 200 OK  (paginated list)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_crud_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> "ScenarioTestBed":
    """Boot a minimal Web + SQL test application."""
    async with scenario_bed(create_crud_app) as scenario:
        yield scenario


class TestWebSqlCrud:
    """Web + SQL full CRUD lifecycle over the real SQLite-backed stack."""

    async def test_create_and_read(self, bed: "ScenarioTestBed") -> None:
        """Creating an item via POST returns 201 and can be read back via GET."""
        resp = await bed.client.post("/api/v1/items", json={"name": "test-item"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.get(f"/api/v1/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-item"

    async def test_update(self, bed: "ScenarioTestBed") -> None:
        """Updating an item via PUT persists the new field values."""
        resp = await bed.client.post("/api/v1/items", json={"name": "before-update"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.put(
            f"/api/v1/items/{item_id}", json={"name": "after-update"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "after-update"

    async def test_delete_returns_404(self, bed: "ScenarioTestBed") -> None:
        """Deleting an item makes subsequent GET return 404."""
        resp = await bed.client.post("/api/v1/items", json={"name": "to-delete"})
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.delete(f"/api/v1/items/{item_id}")
        assert resp.status_code == 204

        resp = await bed.client.get(f"/api/v1/items/{item_id}")
        assert resp.status_code == 404

    async def test_list_with_pagination(self, bed: "ScenarioTestBed") -> None:
        """List endpoint supports page and size query parameters."""
        for i in range(5):
            await bed.client.post("/api/v1/items", json={"name": f"item-{i}"})

        resp = await bed.client.get("/api/v1/items?page=1&size=3")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 3
        assert "total" in body
