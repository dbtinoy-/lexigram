from __future__ import annotations

from datetime import UTC
import io
from typing import TYPE_CHECKING, Any

from lexigram.admin.services.export.service import IExportBackend

if TYPE_CHECKING:
    from lexigram.admin.services.export.scheduler import ExportJob

try:
    from reportlab.lib import colors  # type: ignore[import-untyped]
    from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
    from reportlab.lib.styles import (  # type: ignore[import-untyped]
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.platypus import (  # type: ignore[import-untyped]
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class PdfExportBackend(IExportBackend):
    """Backend for PDF report exports."""

    async def generate_file(
        self,
        job: ExportJob,
        data: list[dict[str, Any]],
        storage: Any,
        export_dir: str,
    ) -> str:
        """Export data to PDF format."""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab is required for PDF export")

        from datetime import datetime

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{job.resource_name}_export_{timestamp}.pdf"
        file_path = f"{export_dir}/{filename}"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph(f"{job.resource_name} Export Report", title_style))
        story.append(Spacer(1, 12))

        # Metadata
        metadata = [
            f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"Total Records: {len(data)}",
            f"Filters Applied: {', '.join(job.filters.keys()) if job.filters else 'None'}",
        ]

        for meta in metadata:
            story.append(Paragraph(meta, styles["Normal"]))
        story.append(Spacer(1, 20))

        if data:
            # Convert to table format
            fieldnames = job.columns if job.columns else list(data[0].keys())

            # Table header
            table_data = [fieldnames]

            # Table rows (limit to first 1000 for PDF)
            for row in data[:1000]:
                table_row = [str(row.get(field, "")) for field in fieldnames]
                table_data.append(table_row)

            # Create table
            table = Table(table_data, repeatRows=1)

            # Table styling
            table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ],
            )
            table.setStyle(table_style)

            story.append(table)

            if len(data) > 1000:
                story.append(Spacer(1, 12))
                story.append(
                    Paragraph(
                        f"Note: Showing first 1000 of {len(data)} records. "
                        "Use CSV/Excel export for complete dataset.",
                        styles["Italic"],
                    ),
                )

        # Build PDF
        doc.build(story)

        # Save to storage
        await storage.upload(
            file_path, buffer.getvalue(), content_type="application/pdf"
        )

        return file_path
