"""R23 import-upload regression tests (B31).

See docs/09-01-2026/19-import-upload.md. The import service worked (R19)
but nothing fed it: no upload route existed in either stack and the
toolbar button was a dead ``hx-get`` to a nonexistent path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from starlette.applications import Starlette
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from lexigram.admin.actions.standard import ImportAction
from lexigram.admin.actions.types import ActionContext
from lexigram.admin.resources.action_handlers import ImportActionHandler

_PKG_ROOT = Path(__file__).resolve().parents[3]


class _FakeDataSource:
    """Create-capable data source recording created rows."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, data: dict[str, Any]) -> Any:
        self.created.append(dict(data))
        return {"id": str(len(self.created)), **data}


def _resource(action: ImportAction | None, data_source: Any) -> Any:
    resource = MagicMock()
    resource.name = "products"
    resource.header_actions = [action] if action else []
    resource.actions = []
    resource._data_source = data_source
    resource.import_max_bytes = None
    return resource


def _upload_app(resource: Any) -> Starlette:
    handler = ImportActionHandler()

    async def endpoint(request: StarletteRequest) -> Response:
        request.scope["admin_action"] = "import"
        request.scope["admin_prefix"] = "/admin"
        return await handler.handle(request, resource)

    return Starlette(routes=[Route("/products/import", endpoint, methods=["POST"])])


class TestHandlerStackUpload:
    def test_upload_imports_rows(self) -> None:
        ds = _FakeDataSource()
        client = TestClient(_upload_app(_resource(ImportAction(), ds)))
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name,sku\nWidget,SKU-1\n", "text/csv")},
            follow_redirects=False,
        )
        # Non-fragment callers are redirected back to the list.
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/products"
        assert ds.created == [{"name": "Widget", "sku": "SKU-1"}]

    def test_fragment_response_carries_toast_and_refresh(self) -> None:
        ds = _FakeDataSource()
        client = TestClient(_upload_app(_resource(ImportAction(), ds)))
        response = client.post(
            "/products/import",
            headers={"HX-Request": "true"},
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
        )
        assert response.status_code == 200
        assert "refresh-list" in response.headers.get("hx-trigger", "")
        assert "Imported 1 of 1" in response.text

    def test_failed_rows_link_the_error_report(self) -> None:
        class _RejectingSource(_FakeDataSource):
            async def create(self, data: dict[str, Any]) -> Any:
                raise ValueError("nope")

        client = TestClient(_upload_app(_resource(ImportAction(), _RejectingSource())))
        response = client.post(
            "/products/import",
            headers={"HX-Request": "true"},
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
        )
        assert response.status_code == 200
        assert "/admin/products/import-report?report_id=" in response.text

    def test_missing_file_is_400(self) -> None:
        client = TestClient(_upload_app(_resource(ImportAction(), _FakeDataSource())))
        response = client.post("/products/import", data={"other": "x"})
        assert response.status_code == 400

    def test_empty_file_is_400(self) -> None:
        client = TestClient(_upload_app(_resource(ImportAction(), _FakeDataSource())))
        response = client.post(
            "/products/import", files={"file": ("rows.csv", b"", "text/csv")}
        )
        assert response.status_code == 400

    def test_oversize_file_is_413(self) -> None:
        resource = _resource(ImportAction(), _FakeDataSource())
        resource.import_max_bytes = 10
        client = TestClient(_upload_app(resource))
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name\n" + b"x" * 100, "text/csv")},
        )
        assert response.status_code == 413

    def test_unconfigured_resource_is_404(self) -> None:
        client = TestClient(_upload_app(_resource(None, _FakeDataSource())))
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
        )
        assert response.status_code == 404

    def test_unsupported_format_is_400(self) -> None:
        client = TestClient(_upload_app(_resource(ImportAction(), _FakeDataSource())))
        response = client.post(
            "/products/import",
            files={"file": ("rows.xlsx", b"\x00\x01", "application/octet-stream")},
        )
        assert response.status_code == 400


class TestControllerStackUpload:
    def _controller(self, action: ImportAction | None) -> Any:
        from lexigram.admin.controllers.resource.imports import ResourceImportMixin
        from lexigram.admin.controllers.resource.meta import ResourceMeta

        ds = _FakeDataSource()

        class _Ctl(ResourceImportMixin):
            meta = ResourceMeta(
                name="products",
                label="Product",
                label_plural="Products",
                prefix="/admin",
            )
            _import_action = action

            def get_data_source(self) -> Any:
                return ds

        ctl = _Ctl()
        ctl._ds = ds  # type: ignore[attr-defined]
        return ctl

    def _app(self, ctl: Any) -> Starlette:
        return Starlette(
            routes=[Route("/products/import", ctl.import_upload, methods=["POST"])]
        )

    def test_upload_imports_rows(self) -> None:
        ctl = self._controller(ImportAction())
        client = TestClient(self._app(ctl))
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert ctl._ds.created == [{"name": "Widget"}]

    def test_missing_capability_is_403(self) -> None:
        ctl = self._controller(ImportAction())
        app = self._app(ctl)

        class _DenyPermissions:
            def __init__(self, inner: Any) -> None:
                self._inner = inner

            async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
                if scope["type"] == "http":
                    scope.setdefault("state", {})["permissions"] = {"can_create": False}
                await self._inner(scope, receive, send)

        client = TestClient(_DenyPermissions(app))  # type: ignore[arg-type]
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
        )
        assert response.status_code == 403
        assert ctl._ds.created == []

    def test_unconfigured_is_404(self) -> None:
        ctl = self._controller(None)
        client = TestClient(self._app(ctl))
        response = client.post(
            "/products/import",
            files={"file": ("rows.csv", b"name\nWidget\n", "text/csv")},
        )
        assert response.status_code == 404


class TestImportButtonRendering:
    def test_button_targets_upload_helper_not_dead_hx_get(self) -> None:
        action = ImportAction()
        ctx = ActionContext(resource_name="products", resource_prefix="/admin/products")
        html = action.render_button(None, ctx)
        assert 'data-import-upload-url="/admin/products/import"' in html
        assert "LexigramImportUpload" in html
        assert ".csv,.json,.jsonl" in html
        assert "hx-get" not in html

    def test_routes_mount_import_post(self) -> None:
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.core.routing import AdminRouter

        router = AdminRouter(config=AdminConfig(prefix="/admin"))
        routes = router._build_resource_routes("products", MagicMock(relations=[]))
        import_routes = [r for r in routes if r.path == "/products/import"]
        assert import_routes, "POST /products/import not mounted"
        assert "POST" in (import_routes[0].methods or set())


class TestSharedScriptShipsHelper:
    def test_data_table_script_defines_import_upload(self) -> None:
        from lexigram.ui.molecules.data_table_client_logic import (
            DataTableScriptRenderer,
        )

        rendered = str(DataTableScriptRenderer.render(["1"]))
        assert "window.LexigramImportUpload" in rendered
        assert "importUploadUrl" in rendered
        assert "X-CSRF-Token" in rendered
