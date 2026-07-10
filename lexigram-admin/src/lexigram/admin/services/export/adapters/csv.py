from __future__ import annotations

import csv
from datetime import UTC
import io
from typing import TYPE_CHECKING, Any

from lexigram.admin.services.export.service import IExportBackend

if TYPE_CHECKING:
    from lexigram.admin.services.export.scheduler import ExportJob


_RISKY_LEADING_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_value(value: Any) -> Any:
    """Neutralize formula/DDE injection in a CSV cell value.

    Spreadsheet applications evaluate cells whose leading character is
    ``=``, ``+``, ``-``, ``@``, or a tab/CR as a live formula or DDE
    trigger when an operator opens the exported file (OWASP CSV-injection
    class). Prefix such values with a single quote so they render as text;
    the prefix is lossless — stripping instead would silently corrupt
    legitimate ``-``/``+``-leading data.

    Args:
        value: Raw cell value from the export data source.

    Returns:
        The sanitized value: non-strings and non-risky strings pass
        through unchanged; risky strings gain a leading ``'``.
    """
    if not isinstance(value, str) or not value:
        return value
    if value[0] in _RISKY_LEADING_CHARS:
        return f"'{value}"
    return value


class CsvExportBackend(IExportBackend):
    """Backend for CSV exports."""

    async def generate_file(
        self,
        job: ExportJob,
        data: list[dict[str, Any]],
        storage: Any,
        export_dir: str,
    ) -> str:
        """Export data to CSV format."""
        from datetime import datetime

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{job.resource_name}_export_{timestamp}.csv"
        file_path = f"{export_dir}/{filename}"

        output = io.StringIO()

        if data:
            # Use specified columns or all columns
            fieldnames = job.columns or list(data[0].keys())

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for row in data:
                # Filter to specified columns if provided
                if job.columns:
                    filtered_row = {k: v for k, v in row.items() if k in job.columns}
                else:
                    filtered_row = row
                sanitized_row = {
                    k: _sanitize_csv_value(v) for k, v in filtered_row.items()
                }
                writer.writerow(sanitized_row)

        # Write to storage
        content = output.getvalue()
        await storage.upload(
            file_path, content.encode("utf-8"), content_type="text/csv"
        )

        return file_path
