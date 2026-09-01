"""Route materialization tests (B11 — path params were dropped).

``collect_instance_routes`` wraps controller methods in a Starlette
handler. Before the fix the wrapper only forwarded ``request``, so any
route with path parameters ("/{role_name}/edit") crashed with a
TypeError at dispatch time.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Mount
from starlette.testclient import TestClient

from lexigram.admin.controllers.route_collection import collect_instance_routes
from lexigram.contracts.web import get, post


class _DemoController:
    prefix = "/demo"

    @get("/")
    async def list_page(self, request) -> Response:
        return PlainTextResponse("list")

    @get("/{item_id:str}/edit")
    async def edit_page(self, request, item_id: str) -> Response:
        return PlainTextResponse(f"edit:{item_id}")

    @post("/{item_id:str}/update")
    async def update(self, request, item_id: str) -> Response:
        return PlainTextResponse(f"update:{item_id}")

    @get("/{a:str}/sub/{b:str}")
    async def two_params(self, request, a: str, b: str) -> Response:
        return PlainTextResponse(f"{a}+{b}")


def _client() -> TestClient:
    routes = collect_instance_routes(_DemoController())
    app = Starlette(routes=[Mount("/admin", routes=routes)])
    return TestClient(app)


class TestPathParamForwarding:
    def test_plain_route_still_works(self) -> None:
        assert _client().get("/admin/demo").text == "list"

    def test_single_path_param_forwarded(self) -> None:
        """B11 regression: this used to 500 with a TypeError."""
        assert _client().get("/admin/demo/abc/edit").text == "edit:abc"

    def test_path_param_forwarded_on_post(self) -> None:
        assert _client().post("/admin/demo/xyz/update").text == "update:xyz"

    def test_multiple_path_params_forwarded(self) -> None:
        assert _client().get("/admin/demo/one/sub/two").text == "one+two"

    def test_encoded_values_are_decoded(self) -> None:
        assert _client().get("/admin/demo/a%40b.c/edit").text == "edit:a@b.c"
