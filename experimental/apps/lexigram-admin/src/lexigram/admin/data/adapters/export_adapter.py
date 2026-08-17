"""Adapter to make IDataSource compatible with ExportService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.data.query import QuerySpec
from lexigram.admin.services.export import IExportDataSource
from lexigram.di.decorators import inject

if TYPE_CHECKING:
    from lexigram.admin.data.data_source import IDataSource


@inject
class ExportDataSourceAdapter(IExportDataSource):
    """Bridges IDataSource to IExportDataSource for ExportService."""

    def __init__(self, data_source: IDataSource) -> None:
        """Initialize with a new-style data source."""
        self.data_source = data_source

    async def get_export_data(
        self,
        filters: dict[str, Any],
        columns: list[str],
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Implementation for IExportDataSource.get_export_data."""
        qs = QuerySpec()

        # Add filters
        for field, val in filters.items():
            if field.endswith("__in"):
                qs = qs.with_where_in(field[:-4], list(val))
            else:
                qs = qs.with_where_eq(field, val)

        # Sort
        if sort_by:
            qs = qs.with_order_by(sort_by, sort_order)

        # Pagination
        per_page = limit or 1000  # Default large limit for export
        page = (offset // per_page + 1) if offset is not None else 1
        qs = qs.with_page(page).with_per_page(per_page)

        # Select
        if columns:
            qs = qs.with_select(*columns)

        result = await self.data_source.find_many(qs)
        return [
            dict(item) if not isinstance(item, dict) else item for item in result.items
        ]

    async def get_export_count(self, filters: dict[str, Any]) -> int:
        """Implementation for IExportDataSource.get_export_count."""
        qs = QuerySpec()
        for field, val in filters.items():
            if field.endswith("__in"):
                qs = qs.with_where_in(field[:-4], list(val))
            else:
                qs = qs.with_where_eq(field, val)

        return await self.data_source.count(qs)

    async def get_column_definitions(self) -> list[dict[str, Any]]:
        """Get column metadata if possible (simplified)."""
        # This would ideally introspect the model or schema
        return []
