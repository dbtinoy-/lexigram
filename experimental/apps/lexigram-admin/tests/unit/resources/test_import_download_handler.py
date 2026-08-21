"""Tests for ImportActionHandler (example CSV / failed-import report downloads)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.actions.standard import ImportAction
from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.action_handlers import ImportActionHandler


class _Report:
    def __init__(self, report_id: str = "rpt-1", source: str = "users.csv") -> None:
        self.id = report_id
        self.source_filename = source

    def to_csv(self) -> str:
        return "row,field,message\n1,__row__,boom"


class _FakeImportService:
    def __init__(self) -> None:
        self._reports = [_Report()]

    def reports(self) -> list[Any]:
        return list(self._reports)

    def get_report(self, report_id: str) -> Any:
        for report in self._reports:
            if report.id == report_id:
                return report
        return None


def _resource(**header_actions: Any) -> Any:
    import_actions = [a for a in header_actions.values() if isinstance(a, ImportAction)]
    resource = MagicMock()
    resource.header_actions = import_actions
    resource.actions = []
    return resource


def _action(service: _FakeImportService | None = None) -> ImportAction:
    return ImportAction(
        import_service=service or _FakeImportService(),
        example_columns=["name", "email"],
        example_filename="users-template.csv",
    )


def _request(action_name: str, query: str = "") -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": f"/admin/users/{action_name}",
        "query_string": query.encode(),
        "headers": [],
        "path_params": {},
        "app": None,
        "state": MagicMock(),
        "admin_action": action_name,
    }
    return Request(scope)


class TestImportActionHandler:
    def test_can_handle_download_actions(self) -> None:
        handler = ImportActionHandler()
        assert handler.can_handle("import-example") is True
        assert handler.can_handle("import-report") is True
        assert handler.can_handle("delete") is False
        assert handler.can_handle("") is False

    def test_find_import_action_scans_header_actions(self) -> None:
        action = _action()
        resource = _resource(header=action)
        assert ImportActionHandler._find_import_action(resource) is action

    def test_find_import_action_scans_actions_fallback(self) -> None:
        action = _action()
        resource = MagicMock()
        resource.header_actions = []
        resource.actions = [action]
        assert ImportActionHandler._find_import_action(resource) is action

    def test_find_import_action_returns_none(self) -> None:
        resource = MagicMock()
        resource.header_actions = []
        resource.actions = []
        assert ImportActionHandler._find_import_action(resource) is None

    @pytest.mark.asyncio
    async def test_handle_import_example_returns_csv_attachment(self) -> None:
        resource = _resource(header=_action())

        response = await ImportActionHandler().handle(
            _request("import-example"), resource
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "users-template.csv" in response.headers["content-disposition"]
        assert "name,email" in response.body.decode()

    @pytest.mark.asyncio
    async def test_handle_import_example_404_without_action(self) -> None:
        resource = _resource()

        response = await ImportActionHandler().handle(
            _request("import-example"), resource
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_import_example_404_without_columns(self) -> None:
        action = ImportAction(import_service=_FakeImportService())
        resource = _resource(header=action)

        response = await ImportActionHandler().handle(
            _request("import-example"), resource
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_import_report_returns_csv_attachment(self) -> None:
        service = _FakeImportService()
        resource = _resource(header=_action(service))

        response = await ImportActionHandler().handle(
            _request("import-report", query="report_id=rpt-1"), resource
        )

        assert response.status_code == 200
        assert "users-import-errors.csv" in response.headers["content-disposition"]
        assert "1,__row__,boom" in response.body.decode()

    @pytest.mark.asyncio
    async def test_handle_import_report_404_unknown_report(self) -> None:
        resource = _resource(header=_action())

        response = await ImportActionHandler().handle(
            _request("import-report", query="report_id=nope"), resource
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_import_report_404_without_action(self) -> None:
        resource = _resource()

        response = await ImportActionHandler().handle(
            _request("import-report", query="report_id=rpt-1"), resource
        )

        assert response.status_code == 404


class TestImportDownloadRouteRegistration:
    """Tests for import download route registration in AdminRouter."""

    def test_import_routes_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]

        assert any("/import-example" in path for path in paths)
        assert any("/import-report" in path for path in paths)

    def test_import_routes_use_get_method(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)

        for route in routes:
            if "import-" in (route.path or ""):
                assert "GET" in route.methods

    def test_import_routes_before_id_catch_all(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]

        assert paths.index("/users/import-example") < paths.index("/users/{id}")
        assert paths.index("/users/import-report") < paths.index("/users/{id}")