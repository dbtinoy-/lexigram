"""Shared export contracts and the built-in JSON export backend."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.admin.data.data_source import (  # type: ignore[attr-defined]
        ExportColumn,
    )
    from lexigram.admin.services.export.scheduler import ExportJob

T = TypeVar("T")


class IExportDataSource(Protocol[T]):  # type: ignore[misc]
    """Protocol for data sources that support advanced exports."""

    async def get_export_data(
        self,
        filters: dict[str, Any],
        columns: list[str],
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get_export_count(self, filters: dict[str, Any]) -> int: ...

    async def get_column_definitions(self) -> list[ExportColumn]: ...


class IExportBackend(Protocol):
    """Protocol for export format backends."""

    async def generate_file(
        self,
        job: ExportJob,
        data: list[dict[str, Any]],
        storage: Any,
        export_dir: str,
    ) -> str: ...


class JsonExportBackend(IExportBackend):
    """Backend for JSON exports using orjson."""

    async def generate_file(
        self,
        job: ExportJob,
        data: list[dict[str, Any]],
        storage: Any,
        export_dir: str,
    ) -> str:
        """Export data to JSON format."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{job.resource_name}_export_{timestamp}.json"
        file_path = f"{export_dir}/{filename}"

        if job.columns:
            output_data = []
            for row in data:
                filtered_row = {k: v for k, v in row.items() if k in job.columns}
                output_data.append(filtered_row)
        else:
            output_data = data

        content = dumps_str(output_data)
        await storage.upload(
            file_path, content.encode("utf-8"), content_type="application/json"
        )
        return file_path
