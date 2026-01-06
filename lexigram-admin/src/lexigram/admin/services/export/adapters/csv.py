from __future__ import annotations

import csv
from datetime import UTC
import io
from typing import TYPE_CHECKING, Any

from lexigram.admin.services.export.service import IExportBackend

if TYPE_CHECKING:
    from lexigram.admin.services.export.scheduler import ExportJob


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
                writer.writerow(filtered_row)

        # Write to storage
        content = output.getvalue()
        await storage.upload(
            file_path, content.encode("utf-8"), content_type="text/csv"
        )

        return file_path
