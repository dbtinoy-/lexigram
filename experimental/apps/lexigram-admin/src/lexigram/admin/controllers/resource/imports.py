"""Import example/report downloads for the resource controller."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource import ResourceController



class ResourceImportMixin:
    """Import example and report downloads."""

    def _find_import_action(self) -> Any:
        """Return the configured ImportAction, or None."""
        return getattr(self, "_import_action", None)

    async def import_example(self, request: Request) -> Response:
        """Serve the resource's import example CSV template as a download."""
        action = self._find_import_action()
        if action is None or not action.example_csv():
            return HTMLResponse(
                "<h1>Import not configured for this resource</h1>",
                status_code=404,
            )
        return Response(
            content=action.example_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{action.example_filename}"'
                )
            },
        )

    async def import_report(self, request: Request) -> Response:
        """Serve a stored failed-import report as a CSV download."""
        action = self._find_import_action()
        report_id = request.query_params.get("report_id", "")
        content = action.report_csv(report_id) if action else None
        if content is None:
            return HTMLResponse("<h1>Report not found</h1>", status_code=404)
        filename = action.report_filename(report_id) or "import-errors.csv"
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
