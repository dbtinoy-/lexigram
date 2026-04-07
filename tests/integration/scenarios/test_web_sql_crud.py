from __future__ import annotations

"""Web + SQL full CRUD lifecycle scenario.

Packages under test: lexigram-web, lexigram-sql
Infrastructure: PostgreSQL

Scenario:
1. Boot a minimal application with WebProvider + SqlProvider.
2. POST  /api/v1/items          → 201 Created  (create)
3. GET   /api/v1/items/{id}     → 200 OK       (read)
4. PUT   /api/v1/items/{id}     → 200 OK       (update)
5. DELETE /api/v1/items/{id}    → 204 No Content (delete)
6. GET   /api/v1/items/{id}     → 404 Not Found  (verify delete)
7. GET   /api/v1/items?page=1&size=10 → 200 OK  (paginated list)
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.scenario, pytest.mark.requires_postgres]


class TestWebSqlCrud:
    """Web + SQL full CRUD lifecycle over real PostgreSQL.

    Boots a minimal application with WebProvider + SqlProvider,
    then exercises create, read, update, delete, and pagination
    via HTTP client requests.
    """

    @pytest.fixture
    async def bed(self) -> None:
        """Boot a minimal Web + SQL test application.

        Yields:
            AppTestBed configured with WebProvider + SqlProvider.
        """
        pytest.skip(
            "TODO: implement create_crud_app factory in conftest.py "
            "and wire AppTestBed.from_factory(create_crud_app)"
        )

    async def test_create_and_read(self, bed: object) -> None:
        """Creating an item via POST returns 201 and can be read back via GET.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "test-item"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-item"

    async def test_update(self, bed: object) -> None:
        """Updating an item via PUT persists the new field values.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "before-update"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.put(f"/api/v1/items/{item_id}", json={"name": "after-update"})  # type: ignore[attr-defined]
        assert resp.status_code == 200
        assert resp.json()["name"] == "after-update"

    async def test_delete_returns_404(self, bed: object) -> None:
        """Deleting an item makes subsequent GET return 404.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        resp = await bed.client.post("/api/v1/items", json={"name": "to-delete"})  # type: ignore[attr-defined]
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        resp = await bed.client.delete(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 204

        resp = await bed.client.get(f"/api/v1/items/{item_id}")  # type: ignore[attr-defined]
        assert resp.status_code == 404

    async def test_list_with_pagination(self, bed: object) -> None:
        """List endpoint supports page and size query parameters.

        Args:
            bed: Booted AppTestBed with HTTP client and live DB.
        """
        for i in range(5):
            await bed.client.post("/api/v1/items", json={"name": f"item-{i}"})  # type: ignore[attr-defined]

        resp = await bed.client.get("/api/v1/items?page=1&size=3")  # type: ignore[attr-defined]
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 3
        assert "total" in body
