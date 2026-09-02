"""R27 import dry-run regression tests.

See docs/09-01-2026/23-import-dry-run.md. A truthy ``dry_run`` form field
validates the upload without committing anything.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.actions.standard.imports import ImportAction
from lexigram.admin.actions.types import ActionContext
from lexigram.serialization import loads_str


class _FakeDataSource:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(dict(data))
        return {"id": str(len(self.created)), **data}


def _ctx(
    content: bytes,
    filename: str = "rows.csv",
    *,
    dry_run: bool = False,
    data_source: _FakeDataSource | None = None,
) -> tuple[ActionContext, _FakeDataSource]:
    ds = data_source or _FakeDataSource()
    metadata: dict[str, Any] = {"file_content": content, "filename": filename}
    if dry_run:
        metadata["dry_run"] = True
    return (
        ActionContext(
            request=None,
            user=object(),
            resource_name="items",
            resource_prefix="/admin/items",
            data_source=ds,
            metadata=metadata,
        ),
        ds,
    )


CSV = b"name,sku\nWidget,SKU-1\nGadget,SKU-2\n"


class TestDryRunAction:
    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self) -> None:
        action = ImportAction()
        ctx, ds = _ctx(CSV, dry_run=True)
        result = await action.execute(None, ctx)
        assert result.is_ok()
        payload = result.unwrap()
        assert payload["dry_run"] is True
        assert payload["created"] == 0
        assert payload["total"] == 2
        assert payload["failed"] == 0
        assert "Nothing was imported" in payload["message"]
        assert ds.created == []

    @pytest.mark.asyncio
    async def test_commit_still_writes(self) -> None:
        action = ImportAction()
        ctx, ds = _ctx(CSV)
        result = await action.execute(None, ctx)
        payload = result.unwrap()
        assert "dry_run" not in payload
        assert payload["created"] == 2
        assert len(ds.created) == 2

    @pytest.mark.asyncio
    async def test_dry_run_then_commit_with_same_action(self) -> None:
        """The real client flow: validate first, then commit."""
        action = ImportAction()
        ds = _FakeDataSource()
        preview_ctx, _ = _ctx(CSV, dry_run=True, data_source=ds)
        assert (await action.execute(None, preview_ctx)).is_ok()
        assert ds.created == []
        commit_ctx, _ = _ctx(CSV, data_source=ds)
        payload = (await action.execute(None, commit_ctx)).unwrap()
        assert payload["created"] == 2
        assert len(ds.created) == 2

    @pytest.mark.asyncio
    async def test_dry_run_errors_get_downloadable_report(self) -> None:
        # Second row has an empty name → row-level validation error when
        # the data source model requires it; use a ragged/blank field.
        bad_csv = b"name,sku\nWidget,SKU-1\n,SKU-2\n"

        class _RequiredNameSource(_FakeDataSource):
            model = None  # plain dict path — validation via required_fields

        action = ImportAction()
        from lexigram.admin.services.import_.service import AdminImportService

        ds = _RequiredNameSource()
        service = AdminImportService(data_source=ds, required_fields=["name"])
        action._import_service = service
        ctx, _ = _ctx(bad_csv, dry_run=True, data_source=ds)
        payload = (await action.execute(None, ctx)).unwrap()
        assert payload["failed"] == 1
        assert payload["dry_run"] is True
        report_id = payload["report_id"]
        # The stored validation report is downloadable via the action.
        csv_out = action.report_csv(report_id)
        assert csv_out is not None
        assert "name" in csv_out
        assert ds.created == []


def _request(form: dict[str, Any], *, htmx: bool = True) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/admin/items/import",
        "query_string": b"",
        "headers": [(b"hx-request", b"true")] if htmx else [],
        "path_params": {},
        "app": None,
        "state": MagicMock(),
        "admin_prefix": "/admin",
        "admin_resource_prefix": "items",
        "admin_action": "import",
    }
    request = Request(scope)
    form_obj = MagicMock()
    form_obj.get = lambda key, default=None: form.get(key, default)
    form_obj.getlist = lambda key: form.get(f"{key}__list", [])
    request.scope["admin_form_data"] = form_obj
    return request


class _Upload:
    def __init__(self, content: bytes, filename: str = "rows.csv") -> None:
        self._content = content
        self.filename = filename

    async def read(self) -> bytes:
        return self._content


class TestDeclarativeRoute:
    def _resource(self, ds: _FakeDataSource) -> Any:
        from lexigram.admin.resources.base import Resource

        class _Items(Resource):
            name = "items"
            header_actions = [ImportAction()]

        resource = _Items()
        resource._data_source = ds
        return resource

    @pytest.mark.asyncio
    async def test_dry_run_field_skips_commit_and_refresh(self) -> None:
        from lexigram.admin.resources.action_handlers import ImportActionHandler

        ds = _FakeDataSource()
        resource = self._resource(ds)
        response = await ImportActionHandler().handle(
            _request({"file": _Upload(CSV), "dry_run": "1"}), resource
        )
        assert response.status_code == 200
        assert ds.created == []
        triggers = loads_str(response.headers["HX-Trigger"])
        assert "refresh-list" not in triggers
        assert "Nothing was imported" in triggers["show-toast"]["message"]

    @pytest.mark.asyncio
    async def test_commit_still_refreshes(self) -> None:
        from lexigram.admin.resources.action_handlers import ImportActionHandler

        ds = _FakeDataSource()
        resource = self._resource(ds)
        response = await ImportActionHandler().handle(
            _request({"file": _Upload(CSV)}), resource
        )
        assert response.status_code == 200
        assert len(ds.created) == 2
        triggers = loads_str(response.headers["HX-Trigger"])
        assert triggers["refresh-list"] is True


class TestControllerRoute:
    def _controller(self, ds: _FakeDataSource) -> Any:
        from lexigram.admin.controllers.resource.imports import ResourceImportMixin
        from lexigram.admin.controllers.resource.meta import ResourceMeta

        class _Controller(ResourceImportMixin):
            def __init__(self) -> None:
                self.meta = ResourceMeta(
                    name="items",
                    label="Item",
                    label_plural="Items",
                    prefix="/admin",
                )
                self._import_action = ImportAction()
                self._ds = ds

            def get_data_source(self) -> Any:
                return self._ds

        return _Controller()

    @pytest.mark.asyncio
    async def test_dry_run_field_skips_commit_and_refresh(self) -> None:
        ds = _FakeDataSource()
        ctl = self._controller(ds)
        response = await ctl.import_upload(
            _request({"file": _Upload(CSV), "dry_run": "true"})
        )
        assert response.status_code == 200
        assert ds.created == []
        triggers = loads_str(response.headers["HX-Trigger"])
        assert "refresh-list" not in triggers
        assert "Nothing was imported" in triggers["show-toast"]["message"]

    @pytest.mark.asyncio
    async def test_commit_still_refreshes(self) -> None:
        ds = _FakeDataSource()
        ctl = self._controller(ds)
        response = await ctl.import_upload(_request({"file": _Upload(CSV)}))
        assert response.status_code == 200
        assert len(ds.created) == 2
        triggers = loads_str(response.headers["HX-Trigger"])
        assert triggers["refresh-list"] is True


class TestClientScript:
    def test_upload_script_validates_then_confirms(self) -> None:
        from lexigram.ui import render_to_string
        from lexigram.ui.molecules.data_table_client_logic import (
            DataTableScriptRenderer,
        )

        rendered = render_to_string(DataTableScriptRenderer.render([]))
        assert "dry_run" in rendered
        assert "Proceed with import?" in rendered
        assert "Import cancelled" in rendered
