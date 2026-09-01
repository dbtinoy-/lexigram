"""Sorting, search and trash must actually change the rendered list.

These three went through the motions -- the URL updated, htmx fired, the
server answered 200 -- while the view never changed. Three separate
defects stacked up on the same request path:

1. Controls fetched ``{prefix}/?...`` while routes are registered as
   ``{prefix}`` (core/routing.py), so every interaction 307-redirected.
2. ``hx-select="#table-data"`` extracts the wrapper itself, but the swap
   used the zone's ``innerHTML`` default, nesting a second ``#table-data``
   inside the live one.
3. ``_available_fields`` only read ``column.name``. Declarative resources
   get ``columns = list(fields)`` -- plain strings -- so the allowlist came
   back empty and ``_sanitize_table_state`` reset every sort to None.

The tests drive the real ResourceHandler over HTTP and assert on what the
data source is actually asked for, since a 200 that renders the unsorted
page is exactly the failure being guarded against.
"""

from __future__ import annotations

import re
from typing import Any

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from lexigram.admin.config import AdminConfig
from lexigram.admin.data import QueryResult
from lexigram.admin.resources.handler import ResourceHandler
from lexigram.admin.resources.roles import RolesResource
from lexigram.contracts.auth import RoleDefinition

HTMX_HEADERS = {"HX-Request": "true", "HX-Target": "table-data"}


class _RecordingDataSource:
    """Captures the query the resource layer actually builds."""

    def __init__(self) -> None:
        self.roles = {
            name: RoleDefinition(name=name) for name in ("zeta", "alpha", "mid")
        }
        self.queries: list[dict[str, Any]] = []

    async def find_one(self, item_id: Any) -> RoleDefinition | None:
        return self.roles.get(str(item_id))

    async def find_many(self, query: Any) -> QueryResult:
        self.queries.append(
            {
                "sort_by": getattr(query, "sort_by", None),
                "sort_order": getattr(query, "sort_order", None),
                "search": getattr(query, "search", None),
                "include_deleted": getattr(query, "include_deleted", None),
            }
        )
        return QueryResult(items=list(self.roles.values()), total=len(self.roles))

    async def count(self, query: Any) -> int:
        return len(self.roles)

    @property
    def last_query(self) -> dict[str, Any]:
        assert self.queries, "data source was never queried"
        return self.queries[-1]


def _app(source: _RecordingDataSource) -> Starlette:
    resource = RolesResource()
    resource._data_source = source
    config = AdminConfig(prefix="/admin", title="Test Admin")
    return Starlette(
        routes=[
            Route(
                "/admin/roles",
                ResourceHandler(config, "roles", "list", resources={"roles": resource}),
            )
        ]
    )


def _client(source: _RecordingDataSource) -> AsyncClient:
    # follow_redirects stays False: a control that redirects is the bug.
    return AsyncClient(
        transport=ASGITransport(app=_app(source)),
        base_url="http://testserver",
        follow_redirects=False,
    )


@pytest.fixture
def source() -> _RecordingDataSource:
    return _RecordingDataSource()


class TestControlUrlsHitTheRouteDirectly:
    """A trailing slash costs every interaction a 307."""

    @pytest.mark.asyncio
    async def test_sort_link_from_the_page_does_not_redirect(
        self, source: _RecordingDataSource
    ) -> None:
        async with _client(source) as client:
            page = await client.get("/admin/roles")
            match = re.search(
                r'<button[^>]*hx-get="([^"]*)"[^>]*hx-target="#table-data"', page.text
            )
            assert match, "no sort control rendered"
            sort_url = match.group(1).replace("&amp;", "&")

            response = await client.get(sort_url, headers=HTMX_HEADERS)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pushed_url_matches_the_fetched_url(
        self, source: _RecordingDataSource
    ) -> None:
        """The address bar and the request must agree, or the URL updates
        while the fetch goes somewhere else."""
        async with _client(source) as client:
            response = await client.get(
                "/admin/roles?sort_by=name", headers=HTMX_HEADERS
            )

            assert response.headers["HX-Push-Url"] == "/admin/roles?sort_by=name"


class TestInteractionsReachTheDataLayer:
    @pytest.mark.asyncio
    async def test_sort_field_survives_the_allowlist(
        self, source: _RecordingDataSource
    ) -> None:
        """RolesResource declares columns as strings; the allowlist used to
        drop them all and silently reset sort_by to None."""
        async with _client(source) as client:
            await client.get(
                "/admin/roles?sort_by=name&sort_order=desc", headers=HTMX_HEADERS
            )

        assert source.last_query["sort_by"] == "name"
        assert source.last_query["sort_order"] == "desc"

    @pytest.mark.asyncio
    async def test_search_reaches_the_query(
        self, source: _RecordingDataSource
    ) -> None:
        async with _client(source) as client:
            await client.get("/admin/roles?search=alp", headers=HTMX_HEADERS)

        assert source.last_query["search"] == "alp"

    @pytest.mark.asyncio
    async def test_trash_toggle_reaches_the_query(
        self, source: _RecordingDataSource
    ) -> None:
        async with _client(source) as client:
            await client.get(
                "/admin/roles?include_deleted=true", headers=HTMX_HEADERS
            )

        assert source.last_query["include_deleted"] is True

    @pytest.mark.asyncio
    async def test_unknown_sort_field_is_still_rejected(
        self, source: _RecordingDataSource
    ) -> None:
        """The allowlist is a security control; widening it must not let an
        arbitrary URL-supplied field through to the data source."""
        async with _client(source) as client:
            await client.get(
                "/admin/roles?sort_by=__secret__", headers=HTMX_HEADERS
            )

        assert source.last_query["sort_by"] != "__secret__"


class TestSwapShapeIsUsable:
    @pytest.mark.asyncio
    async def test_response_carries_exactly_one_data_zone(
        self, source: _RecordingDataSource
    ) -> None:
        """hx-select extracts #table-data itself, so an innerHTML swap would
        nest it inside the live one and orphan the visible subtree."""
        async with _client(source) as client:
            response = await client.get(
                "/admin/roles?sort_by=name", headers=HTMX_HEADERS
            )

        assert response.text.count('id="table-data"') == 1

    @pytest.mark.asyncio
    async def test_data_controls_replace_rather_than_nest(
        self, source: _RecordingDataSource
    ) -> None:
        async with _client(source) as client:
            page = await client.get("/admin/roles")

        for tag in re.findall(r'<[^>]*hx-select="#table-data"[^>]*>', page.text):
            assert 'hx-swap="outerHTML"' in tag

    @pytest.mark.asyncio
    async def test_toolbar_fragments_ride_along(
        self, source: _RecordingDataSource
    ) -> None:
        async with _client(source) as client:
            response = await client.get(
                "/admin/roles?sort_by=name", headers=HTMX_HEADERS
            )

        assert response.text.count("hx-swap-oob") == 2
