"""Import example/report downloads for the resource controller."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response


class ResourceImportMixin:
    """Import upload plus example and report downloads."""

    #: Default upload cap; override per controller via ``import_max_bytes``.
    DEFAULT_IMPORT_MAX_BYTES = 10 * 1024 * 1024

    def _find_import_action(self) -> Any:
        """Return the configured ImportAction, or None."""
        return getattr(self, "_import_action", None)

    async def import_upload(self, request: Request) -> Response:
        """Run the configured ImportAction on an uploaded file (B31).

        Gated on the ``can_create`` capability (imports create records),
        fail-closed like the bulk route.
        """
        from markupsafe import escape

        from lexigram.admin.actions.types import ActionContext
        from lexigram.serialization import dumps_str

        action = self._find_import_action()
        if action is None:
            return HTMLResponse(
                "<h1>Import not configured for this resource</h1>",
                status_code=404,
            )

        capabilities = getattr(getattr(request, "state", None), "permissions", None)
        if isinstance(capabilities, dict) and not capabilities.get("can_create", False):
            return HTMLResponse("Forbidden", status_code=403)

        form = request.scope.get("admin_form_data")
        if form is None:
            form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            return HTMLResponse("No file uploaded", status_code=400)

        content = await upload.read()
        if not content:
            return HTMLResponse("Uploaded file is empty", status_code=400)
        max_bytes = (
            getattr(self, "import_max_bytes", None) or self.DEFAULT_IMPORT_MAX_BYTES
        )
        if len(content) > max_bytes:
            return HTMLResponse(
                f"Uploaded file exceeds the {max_bytes} byte import limit",
                status_code=413,
            )

        filename = getattr(upload, "filename", "") or "import.csv"
        resource_prefix = f"{self.meta.prefix}/{self.meta.name}"  # type: ignore[attr-defined]
        ctx = ActionContext(
            request=request,
            user=getattr(getattr(request, "state", None), "user", None),
            resource_name=self.meta.name,  # type: ignore[attr-defined]
            resource_prefix=resource_prefix,
            data_source=self.get_data_source(),  # type: ignore[attr-defined]
            metadata={"file_content": content, "filename": str(filename)},
        )
        result = await action.execute(None, ctx)
        if result.is_err():
            error = result.unwrap_err()
            message = str(getattr(error, "message", None) or error)
            return HTMLResponse(str(escape(message)), status_code=400)

        payload = result.unwrap()
        message = str(payload.get("message", "Import complete"))
        parts = [f"<p>{escape(message)}</p>"]
        report_id = payload.get("report_id")
        if report_id:
            report_url = (
                f"{resource_prefix}/import-report?report_id={escape(str(report_id))}"
            )
            parts.append(
                f'<a href="{report_url}" download>Download failed-row report</a>'
            )

        if request.headers.get("hx-request"):
            response = HTMLResponse("".join(parts))
            response.headers["HX-Trigger"] = dumps_str(
                {
                    "refresh-list": True,
                    "show-toast": {
                        "message": message,
                        "type": "success" if not payload.get("failed") else "warning",
                    },
                }
            )
            return response
        return RedirectResponse(url=resource_prefix, status_code=302)

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
