from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from lexigram.admin.services.export.service import IExportBackend
from lexigram.admin.services.export.xlsx import (
    HAS_OPENPYXL,
    OPENPYXL_MISSING_MESSAGE,
    XLSX_CONTENT_TYPE,
    encode_rows_as_xlsx,
)

if TYPE_CHECKING:
    from lexigram.admin.services.export.scheduler import ExportJob


class ExcelExportBackend(IExportBackend):
    """Backend for Excel exports.

    R29: workbook construction lives in the shared
    :func:`~lexigram.admin.services.export.xlsx.encode_rows_as_xlsx`
    encoder (also used by the direct-download bulk exports), which
    sanitizes formula-injection payloads and coerces cell values openpyxl
    cannot store natively (dict/list/bytes/…) instead of crashing.
    """

    async def generate_file(
        self,
        job: ExportJob,
        data: list[dict[str, Any]],
        storage: Any,
        export_dir: str,
    ) -> str:
        """Export data to Excel format."""
        if not HAS_OPENPYXL:
            raise ImportError(OPENPYXL_MISSING_MESSAGE)

        from datetime import datetime

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{job.resource_name}_export_{timestamp}.xlsx"
        file_path = f"{export_dir}/{filename}"

        payload = encode_rows_as_xlsx(data, fieldnames=job.columns or None)
        await storage.upload(
            file_path,
            payload,
            content_type=XLSX_CONTENT_TYPE,
        )

        return file_path
