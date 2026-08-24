from __future__ import annotations

import pytest

pytestmark = [pytest.mark.scenario]

import httpx
from starlette.applications import Starlette

from tests.scenario.test_admin_ui_controls import (  # noqa: E402
    FakeDataSource,
    ScenarioController,
    _make_records,
)


@pytest.fixture
def ds() -> FakeDataSource:
    return FakeDataSource(_make_records(25))


@pytest.fixture
def controller(ds: FakeDataSource) -> ScenarioController:
    return ScenarioController(data_source=ds)


@pytest.fixture
def app(controller: ScenarioController) -> Starlette:
    routes = controller.get_routes()
    return Starlette(routes=routes)


@pytest.fixture
async def client(app: Starlette):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


class TestCRUD:
    async def test_detail(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1")
        assert resp.status_code == 200
        assert "User 1" in resp.text

    async def test_detail_not_found(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/99999")
        assert resp.status_code == 404

    async def test_create_form(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/create")
        assert resp.status_code == 200

    async def test_create_submit(
        self, client: httpx.AsyncClient, ds: FakeDataSource
    ) -> None:
        before = len(ds._records)
        resp = await client.post(
            "/item", data={"name": "New Person", "email": "new@test.com"}
        )
        assert resp.status_code in (200, 302)
        assert len(ds._records) == before + 1

    async def test_edit_form(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1/edit")
        assert resp.status_code == 200

    async def test_update_via_put(self, client: httpx.AsyncClient) -> None:
        resp = await client.request(
            "PUT", "/item/1", data={"name": "Updated", "email": "u@test.com"}
        )
        assert resp.status_code in (200, 302)

    async def test_delete(self, client: httpx.AsyncClient) -> None:
        resp = await client.delete("/item/1")
        assert resp.status_code in (200, 302)


class TestBulkAction:
    async def test_bulk_delete(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/item/bulk",
            data={"action": "delete", "ids": ["1", "2"]},
            headers={"hx-request": "true", "hx-target": "main"},
        )
        assert resp.status_code == 200

    async def test_bulk_delete_redirects_without_htmx(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/item/bulk", data={"action": "delete", "ids": ["1", "2"]}
        )
        assert resp.status_code in (302, 200)
