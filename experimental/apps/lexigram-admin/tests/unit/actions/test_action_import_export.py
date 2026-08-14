"""Tests for import/export action wiring in actions/standard.py."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.standard import (
    ExportAction,
    ExportBulkAction,
    ImportAction,
    ImportBulkAction,
)
from lexigram.admin.actions.types import ActionContext
from lexigram.admin.data.adapters.export_adapter import ExportDataSourceAdapter
from lexigram.admin.data.query import FilterOperator, QuerySpec
from lexigram.admin.services.export import ExportFormat
from lexigram.result import Ok, Result


class _FakeDataSource:
    """Minimal IDataSource double that records queries and creations."""

    def __init__(self, items: list[dict[str, Any]], total: int) -> None:
        self.items = items
        self.total = total
        self.queries: list[QuerySpec] = []
        self.created: list[dict[str, Any]] = []

    async def find_many(self, qs: QuerySpec) -> SimpleNamespace:
        self.queries.append(qs)
        return SimpleNamespace(items=self.items, total=self.total)

    async def count(self, qs: QuerySpec) -> int:
        self.queries.append(qs)
        return self.total

    async def create(self, row: dict[str, Any]) -> SimpleNamespace:
        self.created.append(row)
        return SimpleNamespace(id=str(len(self.created)))


class _FakeExportService:
    """ExportService double that records job creation and executes in-memory."""

    def __init__(self, job: SimpleNamespace) -> None:
        self._job = job
        self.create_calls: list[dict[str, Any]] = []
        self.executed: list[tuple[str, Any]] = []

    def create_job(self, **kwargs: Any) -> str:
        self.create_calls.append(kwargs)
        return "job-1"

    async def execute_export(self, job_id: str, data_source: Any) -> Result[Any, Any]:
        self.executed.append((job_id, data_source))
        return Ok(self._job)


class _FakeImportService:
    """AdminImportService double that records parse and commit calls."""

    def __init__(
        self,
        parse_result: Any,
        commit_result: Any,
        reports: list[Any] | None = None,
    ) -> None:
        self._parse_result = parse_result
        self._commit_result = commit_result
        self._reports = reports or []
        self.parse_calls: list[tuple[bytes, str]] = []
        self.commits: list[Any] = []

    async def parse(self, content: bytes, filename: str) -> Any:
        self.parse_calls.append((content, filename))
        return self._parse_result

    async def commit(self, job: Any) -> Any:
        self.commits.append(job)
        return self._commit_result

    def reports(self) -> list[Any]:
        return self._reports

    def get_report(self, report_id: str) -> Any:
        for report in self._reports:
            if report.id == report_id:
                return report
        return None


def _job(total_records: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        job_id="job-1",
        total_records=total_records,
        download_url="/admin/exports/download/exports/users_export.csv",
        file_path="exports/users_export.csv",
    )


class TestExportActionExecute:
    @pytest.mark.asyncio
    async def test_execute_runs_export_with_record_id_filter(self) -> None:
        service = _FakeExportService(_job())
        action = ExportAction(
            export_service=service,
            data_source=_FakeDataSource(items=[], total=1),
        )
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": "42"}, ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert payload["job_id"] == "job-1"
        assert payload["total_records"] == 1
        assert payload["download_url"].startswith("/admin/exports/download")
        assert payload["file_path"] == "exports/users_export.csv"
        assert service.create_calls[0]["resource_name"] == "users"
        assert service.create_calls[0]["file_format"] == ExportFormat.CSV
        assert service.create_calls[0]["filters"] == {"id": "42"}
        assert isinstance(service.executed[0][1], ExportDataSourceAdapter)

    @pytest.mark.asyncio
    async def test_execute_uses_context_data_source(self) -> None:
        ds = _FakeDataSource(items=[], total=1)
        service = _FakeExportService(_job())
        action = ExportAction(export_service=service)
        ctx = ActionContext(resource_name="users", data_source=ds)

        result = await action.execute({"id": "42"}, ctx)

        assert result.is_ok()
        assert service.executed[0][1].data_source is ds

    @pytest.mark.asyncio
    async def test_execute_resolves_service_from_request_container(self) -> None:
        service = _FakeExportService(_job())
        action = ExportAction(data_source=_FakeDataSource(items=[], total=1))

        class _Container:
            async def resolve(self, cls: Any) -> Any:
                return service

        class _App:
            state = SimpleNamespace(container=None)

        class _Request:
            state = SimpleNamespace(container=_Container())
            app = _App()

        ctx = ActionContext(resource_name="users", request=_Request())

        result = await action.execute({"id": "42"}, ctx)

        assert result.is_ok()
        assert service.create_calls[0]["filters"] == {"id": "42"}

    @pytest.mark.asyncio
    async def test_execute_missing_data_source_returns_err(self) -> None:
        action = ExportAction(export_service=_FakeExportService(_job()))
        ctx = ActionContext(resource_name="users")

        result = await action.execute({"id": "42"}, ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)
        assert "data source" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_missing_service_returns_err(self) -> None:
        action = ExportAction(data_source=_FakeDataSource(items=[], total=1))
        ctx = ActionContext(resource_name="users")

        result = await action.execute({"id": "42"}, ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)
        assert "ExportService" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_no_record_id_returns_err(self) -> None:
        action = ExportAction(
            export_service=_FakeExportService(_job()),
            data_source=_FakeDataSource(items=[], total=1),
        )
        ctx = ActionContext(resource_name="users")

        result = await action.execute({}, ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


class TestExportBulkActionExecute:
    @pytest.mark.asyncio
    async def test_execute_runs_export_with_id_in_filter(self) -> None:
        service = _FakeExportService(_job(total_records=2))
        action = ExportBulkAction(
            export_service=service,
            data_source=_FakeDataSource(items=[], total=2),
        )
        ctx = ActionContext(resource_name="users")

        result = await action.execute([{"id": "1"}, {"id": "2"}], ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert payload["total_records"] == 2
        assert service.create_calls[0]["filters"] == {"id__in": ["1", "2"]}
        assert "2" in payload["message"]

    @pytest.mark.asyncio
    async def test_execute_missing_ids_returns_err(self) -> None:
        action = ExportBulkAction(
            export_service=_FakeExportService(_job()),
            data_source=_FakeDataSource(items=[], total=1),
        )
        ctx = ActionContext(resource_name="users")

        result = await action.execute([{}], ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)

    @pytest.mark.asyncio
    async def test_execute_missing_data_source_returns_err(self) -> None:
        action = ExportBulkAction(export_service=_FakeExportService(_job()))
        ctx = ActionContext(resource_name="users")

        result = await action.execute([{"id": "1"}], ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)

    @pytest.mark.asyncio
    async def test_execute_missing_service_returns_err(self) -> None:
        action = ExportBulkAction(data_source=_FakeDataSource(items=[], total=1))
        ctx = ActionContext(resource_name="users")

        result = await action.execute([{"id": "1"}], ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


class TestImportAction:
    @pytest.mark.asyncio
    async def test_execute_parses_and_commits_from_metadata(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace(created=2, failed=0, total=2)),
        )
        action = ImportAction(import_service=service)
        ctx = ActionContext(
            resource_name="users",
            metadata={"file_content": b"name\nAda\nBob", "filename": "users.csv"},
        )

        result = await action.execute(None, ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert payload["created"] == 2
        assert payload["failed"] == 0
        assert payload["total"] == 2
        assert service.parse_calls == [(b"name\nAda\nBob", "users.csv")]
        assert len(service.commits) == 1

    @pytest.mark.asyncio
    async def test_execute_without_service_builds_from_data_source(self) -> None:
        ds = _FakeDataSource(items=[], total=0)
        action = ImportAction(data_source=ds)
        ctx = ActionContext(
            resource_name="users", metadata={"file_content": b"name\nAda"}
        )

        result = await action.execute(None, ctx)

        assert result.is_ok()
        assert ds.created == [{"name": "Ada"}]

    @pytest.mark.asyncio
    async def test_execute_missing_file_content_returns_err(self) -> None:
        action = ImportAction()
        ctx = ActionContext(resource_name="users")

        result = await action.execute(None, ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)
        assert "file content" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_without_service_or_data_source_returns_err(self) -> None:
        action = ImportAction()
        ctx = ActionContext(
            resource_name="users", metadata={"file_content": b"name\nAda"}
        )

        result = await action.execute(None, ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)

    @pytest.mark.asyncio
    async def test_execute_surfaces_failed_import_report(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace(created=1, failed=2, total=3)),
            reports=[
                SimpleNamespace(id="rpt-abc", source_filename="users.csv"),
            ],
        )
        action = ImportAction(import_service=service)
        ctx = ActionContext(
            resource_name="users",
            metadata={"file_content": b"name\nAda\nBob\nCyd", "filename": "users.csv"},
        )

        result = await action.execute(None, ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert payload["report_id"] == "rpt-abc"
        assert payload["report_filename"] == "users-import-errors.csv"

    @pytest.mark.asyncio
    async def test_execute_omits_report_keys_when_no_failures(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace(created=2, failed=0, total=2)),
            reports=[SimpleNamespace(id="rpt-abc", source_filename="users.csv")],
        )
        action = ImportAction(import_service=service)
        ctx = ActionContext(
            resource_name="users",
            metadata={"file_content": b"name\nAda\nBob", "filename": "users.csv"},
        )

        result = await action.execute(None, ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert "report_id" not in payload
        assert "report_filename" not in payload


class TestImportBulkAction:
    @pytest.mark.asyncio
    async def test_execute_parses_and_commits(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace(created=2, failed=1, total=3)),
        )
        action = ImportBulkAction(import_service=service)
        ctx = ActionContext(
            resource_name="users",
            metadata={"file_content": b"name\nAda\nBob\nCyd", "filename": "users.csv"},
        )

        result = await action.execute([{"id": "1"}, {"id": "2"}], ctx)

        assert result.is_ok()
        payload = result.unwrap()
        assert payload["created"] == 2
        assert payload["failed"] == 1
        assert payload["total"] == 3
        assert len(service.commits) == 1

    @pytest.mark.asyncio
    async def test_execute_missing_file_content_returns_err(self) -> None:
        action = ImportBulkAction()
        ctx = ActionContext(resource_name="users")

        result = await action.execute([], ctx)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


def _report(report_id: str = "rpt-1", source: str = "users.csv") -> SimpleNamespace:
    return SimpleNamespace(
        id=report_id,
        source_filename=source,
        to_csv=lambda: "row,field,message\n1,__row__,boom",
    )


class TestImportActionReportDownload:
    @pytest.mark.asyncio
    async def test_report_csv_returns_content_for_known_report(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace()),
            reports=[_report()],
        )
        action = ImportAction(import_service=service)

        assert action.report_csv("rpt-1") == "row,field,message\n1,__row__,boom"

    @pytest.mark.asyncio
    async def test_report_csv_none_for_unknown_or_missing_service(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace()),
            reports=[_report()],
        )
        action = ImportAction(import_service=service)

        assert action.report_csv("nope") is None
        assert ImportAction().report_csv("rpt-1") is None

    @pytest.mark.asyncio
    async def test_report_filename_derives_from_source(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace()),
            reports=[_report(source="users-data.csv")],
        )
        action = ImportAction(import_service=service)

        assert action.report_filename("rpt-1") == "users-data-import-errors.csv"
        assert action.report_filename("nope") is None

    @pytest.mark.asyncio
    async def test_example_filename_property(self) -> None:
        action = ImportAction(example_filename="users-template.csv")

        assert action.example_filename == "users-template.csv"

    @pytest.mark.asyncio
    async def test_bulk_action_report_csv(self) -> None:
        service = _FakeImportService(
            parse_result=Ok(SimpleNamespace()),
            commit_result=Ok(SimpleNamespace()),
            reports=[_report()],
        )
        action = ImportBulkAction(import_service=service)

        assert action.report_csv("rpt-1") == "row,field,message\n1,__row__,boom"
        assert action.report_filename("rpt-1") == "users-import-errors.csv"


class TestExportDataSourceAdapterFilters:
    @pytest.mark.asyncio
    async def test_get_export_data_maps_in_filters(self) -> None:
        ds = _FakeDataSource(items=[{"id": "1"}, {"id": "2"}], total=2)
        adapter = ExportDataSourceAdapter(data_source=ds)

        data = await adapter.get_export_data(filters={"id__in": ["1", "2"]}, columns=[])

        assert data == [{"id": "1"}, {"id": "2"}]
        where = ds.queries[0].where
        assert len(where) == 1
        assert where[0].field == "id"
        assert where[0].operator == FilterOperator.IN
        assert where[0].value == ["1", "2"]

    @pytest.mark.asyncio
    async def test_get_export_data_maps_eq_filters(self) -> None:
        ds = _FakeDataSource(items=[{"id": "1"}], total=1)
        adapter = ExportDataSourceAdapter(data_source=ds)

        await adapter.get_export_data(filters={"id": "1"}, columns=[])

        where = ds.queries[0].where
        assert where[0].field == "id"
        assert where[0].operator == FilterOperator.EQ
        assert where[0].value == "1"

    @pytest.mark.asyncio
    async def test_get_export_count_maps_in_filters(self) -> None:
        ds = _FakeDataSource(items=[], total=2)
        adapter = ExportDataSourceAdapter(data_source=ds)

        count = await adapter.get_export_count(filters={"id__in": ["1", "2"]})

        assert count == 2
        where = ds.queries[0].where
        assert where[0].field == "id"
        assert where[0].operator == FilterOperator.IN
