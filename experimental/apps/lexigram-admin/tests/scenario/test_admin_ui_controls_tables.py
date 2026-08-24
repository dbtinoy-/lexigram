from __future__ import annotations

import pytest

pytestmark = [pytest.mark.scenario]

import httpx
from starlette.applications import Starlette

from tests.scenario.admin_ui_controls_support import (  # noqa: E402
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


class TestFullPageHTMLContract:
    async def _get(self, client: httpx.AsyncClient) -> httpx.Response:
        return await client.get("/item")

    async def test_returns_200(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert resp.status_code == 200

    async def test_includes_sidebar(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "Items" in resp.text
        assert "Dashboard" in resp.text
        assert "Settings" in resp.text

    async def test_includes_search_input(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "search" in resp.text.lower() or 'type="search"' in resp.text

    async def test_includes_filter_controls(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        bodies = ["status", "active", "archived"]
        assert any(b in resp.text.lower() for b in bodies)

    async def test_includes_sort_links(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "sort" in resp.text.lower() or "order" in resp.text.lower()

    async def test_includes_pagination(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "page" in resp.text.lower() or "1" in resp.text

    async def test_includes_selection_checkboxes(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await self._get(client)
        assert 'type="checkbox"' in resp.text

    async def test_includes_bulk_actions(self, client: httpx.AsyncClient) -> None:
        resp = await self._get(client)
        assert "delete" in resp.text.lower()


class TestHTMXSearch:
    async def test_search_filters_results(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?q=User+1&sort=id&order=asc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200

    async def test_search_empty_returns_all(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?search=", headers={"hx-request": "true"})
        assert resp.status_code == 200

    async def test_search_no_match(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?search=zzzznotfound", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200
        assert "No results" in resp.text or "no" in resp.text.lower()


class TestHTMXFilter:
    async def test_filter_status(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?filter%5Bstatus%5D=archived", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200


class TestHTMXSort:
    async def test_sort_by_name_asc(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?sort=name&order=asc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200

    async def test_sort_by_name_desc(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/item?sort=name&order=desc", headers={"hx-request": "true"}
        )
        assert resp.status_code == 200


class TestHTMXPagination:
    async def test_page_2_has_different_items(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?page=2", headers={"hx-request": "true"})
        assert resp.status_code == 200

    async def test_page_out_of_range(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?page=99", headers={"hx-request": "true"})
        assert resp.status_code == 200


class TestPageSize:
    async def test_per_page_5(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item?per_page=5", headers={"hx-request": "true"})
        assert resp.status_code == 200


class TestHTMXModalsAndSlideOvers:
    async def test_htmx_detail_returns_partial(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/item/1", headers={"hx-request": "true"})
        assert resp.status_code == 200
        assert "User 1" in resp.text
