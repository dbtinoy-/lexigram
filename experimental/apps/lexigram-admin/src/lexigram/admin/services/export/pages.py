"""Export center — jobs page, background creation, and cancel (R30).

Server-rendered UI for the job-based export lifecycle (R28):

* ``GET {prefix}/exports`` — full-shell page listing the requester's
  export jobs (all jobs for superusers) with download links for
  COMPLETED jobs (R28 route) and cancel buttons for PENDING/PROCESSING
  ones, plus a "New export" form.
* ``POST {prefix}/exports`` — creates a job for a mounted resource and
  starts it in the background via the service's task manager.
* ``POST {prefix}/exports/{job_id}/cancel`` — cancels a running or
  pending job (B21 semantics), same ownership rule as download.

Security model (fail-closed, shared with ``download.py``):

* every handler requires an authenticated user (401);
* job visibility/actions are owner-or-superuser (``may_access_job``);
* creation requires ``PermissionService.can_list`` on the target
  resource when a permission service is available, and falls back to
  superuser-only when it is not.

POST handlers read ``request.scope["admin_form_data"]`` first — the CSRF
middleware pre-reads the body, so a bare ``request.form()`` would hang.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from lexigram.admin.services.export.download import may_access_job, requester_id
from lexigram.admin.services.export.scheduler import ExportFormat, ExportStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

    from lexigram.admin.services.export.scheduler import ExportJob
    from lexigram.admin.services.export.service import ExportService

logger = get_logger(__name__)

#: Formats offered by the export center. PDF stays out until the backend
#: has a real layout story (and its own optional dependency check).
EXPORT_PAGE_FORMATS: dict[str, ExportFormat] = {
    "csv": ExportFormat.CSV,
    "json": ExportFormat.JSON,
    "xlsx": ExportFormat.EXCEL,
}

#: Jobs listed on the page (most recent first, service-side ordering).
_MAX_LISTED_JOBS = 50

_STATUS_TEXT_CLASSES: dict[ExportStatus, str] = {
    ExportStatus.PENDING: "text-muted-foreground",
    ExportStatus.PROCESSING: "text-primary",
    ExportStatus.COMPLETED: "text-success",
    ExportStatus.FAILED: "text-destructive",
    ExportStatus.CANCELLED: "text-muted-foreground",
}


def _human_size(size: int | None) -> str:
    """Humanize a byte count (``0`` / unknown renders as an em dash)."""
    if not size or size <= 0:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"  # pragma: no cover — loop always returns


def _format_dt(value: datetime | None) -> str:
    """Render a timestamp compactly (UTC, minute precision)."""
    if not isinstance(value, datetime):
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


class ExportCenter:
    """Handlers for the export center page, creation, and cancellation.

    Args:
        export_service: DI singleton owning the job manager and storage.
        resources: Mounted resource instances keyed by name (used for the
            "New export" form and to resolve data sources).
        config: Admin config (mount prefix + CSRF secret for the forms).
        renderer: Engine ``AdminRenderer`` for full-shell pages.
        permission_service: Optional RBAC service; when present, creation
            requires ``can_list`` on the target resource, otherwise
            creation is superuser-only.
    """

    def __init__(
        self,
        export_service: ExportService,
        resources: dict[str, Any],
        config: Any,
        renderer: Any,
        permission_service: Any = None,
    ) -> None:
        self._service = export_service
        self._resources = dict(resources or {})
        self._config = config
        self._renderer = renderer
        self._permissions = permission_service

    # -- shared helpers ----------------------------------------------------

    @property
    def _prefix(self) -> str:
        prefix = getattr(self._config, "prefix", None) or "/admin"
        return str(prefix).rstrip("/")

    @staticmethod
    def _user(request: Request) -> Any:
        return getattr(request.state, "user", None)

    def _form_data(self, request: Request) -> Any:
        """Return the pre-read form mapping (CSRF middleware fills it)."""
        return request.scope.get("admin_form_data")

    def _csrf_token(self, request: Request) -> str:
        """Mint/reuse the request CSRF token (same recipe as forms)."""
        existing = getattr(getattr(request, "state", None), "csrf_token", None)
        if existing:
            return str(existing)
        try:
            from lexigram.admin.auth.services.csrf_service import AdminCsrfService

            session = getattr(request, "session", {}) or {}
            session_id = session.get("csrf_session_id") or session.get(
                "admin_user_id", "anonymous"
            )
            token = AdminCsrfService(
                secret=self._config.auth.session_secret.get_secret_value()
            ).generate_token(session_id)
            request.state.csrf_token = token
            return token
        except Exception:  # noqa: BLE001 — page still renders; POST will 403
            logger.warning("admin.export_center.csrf_mint_failed", exc_info=True)
            return ""

    async def _can_create(self, user: Any, resource_name: str) -> bool:
        """Fail-closed creation gate (permission service or superuser)."""
        if self._permissions is not None:
            try:
                return bool(await self._permissions.can_list(user, resource_name))
            except Exception:  # noqa: BLE001 — authorization fails closed
                logger.warning("admin.export_center.permission_check_failed")
                return False
        return getattr(user, "is_superuser", False) is True

    async def _visible_resources(self, user: Any) -> list[str]:
        """Resource names the user may export (drives the form select)."""
        names = []
        for name in sorted(self._resources):
            if await self._can_create(user, name):
                names.append(name)
        return names

    def _jobs_for(self, user: Any) -> list[ExportJob]:
        if getattr(user, "is_superuser", False) is True:
            return self._service.list_jobs(limit=_MAX_LISTED_JOBS)
        uid = requester_id(user)
        if uid is None:
            return []
        return self._service.list_jobs(user_id=uid, limit=_MAX_LISTED_JOBS)

    # -- GET /exports -------------------------------------------------------

    async def page(self, request: Request) -> Response:
        """Render the export center page inside the admin shell."""
        user = self._user(request)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)

        from lexigram.ui import el, render_to_string

        csrf_token = self._csrf_token(request)
        exportable = await self._visible_resources(user)
        jobs = self._jobs_for(user)

        content = render_to_string(
            el(
                "div",
                self._header(),
                self._create_form(exportable, csrf_token),
                self._jobs_region(jobs, csrf_token),
                class_="space-y-6",
            )
        )
        return self._renderer.render_page(
            content,
            request=request,
            title="Exports",
            breadcrumbs=[
                {"label": "Home", "url": f"{self._prefix}/"},
                {"label": "Exports", "url": f"{self._prefix}/exports"},
            ],
        )

    def _header(self) -> Any:
        from lexigram.ui import el

        return el(
            "div",
            el("h1", "Exports", class_="text-2xl font-bold text-foreground"),
            el(
                "p",
                "Run background exports and download the results. "
                "Jobs you start appear below.",
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )

    def _create_form(self, resource_names: list[str], csrf_token: str) -> Any:
        from lexigram.ui import el

        if not resource_names:
            return el(
                "p",
                "You do not have permission to start exports.",
                class_="text-muted-foreground text-sm",
            )
        select_class = (
            "border border-border rounded-md px-3 py-2 bg-background "
            "text-foreground text-sm"
        )
        return el(
            "form",
            el("input", type="hidden", name="csrf_token", value=csrf_token),
            el(
                "select",
                *[el("option", name, value=name) for name in resource_names],
                name="resource",
                class_=select_class,
                aria_label="Resource",
            ),
            el(
                "select",
                *[el("option", fmt.upper(), value=fmt) for fmt in EXPORT_PAGE_FORMATS],
                name="format",
                class_=select_class,
                aria_label="Format",
            ),
            el(
                "button",
                "Start export",
                type="submit",
                class_=(
                    "bg-primary text-primary-foreground rounded-md px-4 py-2 "
                    "text-sm font-medium hover:opacity-90"
                ),
            ),
            method="post",
            action=f"{self._prefix}/exports",
            class_="flex flex-wrap items-center gap-3",
        )

    # -- GET /exports/jobs ---------------------------------------------------

    async def jobs_fragment(self, request: Request) -> Response:
        """Return the jobs region only, for HTMX polling swaps."""
        user = self._user(request)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)

        from lexigram.ui import render_to_string

        csrf_token = self._csrf_token(request)
        jobs = self._jobs_for(user)
        return HTMLResponse(render_to_string(self._jobs_region(jobs, csrf_token)))

    def _jobs_region(self, jobs: list[ExportJob], csrf_token: str) -> Any:
        """Wrap the jobs table in a self-updating region.

        While any listed job is still active the region carries HTMX
        polling attributes (``hx-get`` + ``every 3s`` + ``outerHTML``
        swap); once every job is terminal the attributes are omitted, so
        the final swap naturally stops the polling loop.
        """
        from lexigram.ui import el

        polling: dict[str, str] = {}
        if any(
            job.status in (ExportStatus.PENDING, ExportStatus.PROCESSING)
            for job in jobs
        ):
            polling = {
                "hx_get": f"{self._prefix}/exports/jobs",
                "hx_trigger": "every 3s",
                "hx_swap": "outerHTML",
            }
        return el(
            "div",
            self._jobs_table(jobs, csrf_token),
            id="exports-jobs",
            data_testid="exports-jobs-region",
            **polling,
        )

    def _jobs_table(self, jobs: list[ExportJob], csrf_token: str) -> Any:
        from lexigram.ui import el

        if not jobs:
            return el(
                "p",
                "No export jobs yet. Start one above.",
                class_="text-muted-foreground text-sm",
                data_testid="exports-empty",
            )

        head = el(
            "tr",
            *[
                el(
                    "th",
                    label,
                    class_="text-left text-xs font-medium "
                    "text-muted-foreground px-3 py-2",
                )
                for label in (
                    "Resource",
                    "Format",
                    "Status",
                    "Progress",
                    "Records",
                    "Size",
                    "Created",
                    "Actions",
                )
            ],
        )
        body_rows = [self._job_row(job, csrf_token) for job in jobs]
        refresh = el(
            "a",
            "Refresh",
            href=f"{self._prefix}/exports",
            class_="text-primary text-sm underline",
        )
        return el(
            "div",
            el(
                "table",
                el("thead", head),
                el("tbody", *body_rows),
                class_="w-full border-collapse",
                data_testid="exports-table",
            ),
            refresh,
            class_="space-y-3",
        )

    def _job_row(self, job: ExportJob, csrf_token: str) -> Any:
        from lexigram.ui import el

        cell = "px-3 py-2 text-sm text-foreground border-t border-border"
        status_class = _STATUS_TEXT_CLASSES.get(job.status, "text-foreground")

        actions: list[Any] = []
        if job.status is ExportStatus.COMPLETED and job.download_url:
            actions.append(
                el(
                    "a",
                    "Download",
                    href=job.download_url,
                    class_="text-primary underline",
                )
            )
        if job.status in (ExportStatus.PENDING, ExportStatus.PROCESSING):
            actions.append(
                el(
                    "form",
                    el("input", type="hidden", name="csrf_token", value=csrf_token),
                    el(
                        "button",
                        "Cancel",
                        type="submit",
                        class_="text-destructive underline text-sm",
                    ),
                    method="post",
                    action=f"{self._prefix}/exports/{job.job_id}/cancel",
                    class_="inline",
                )
            )
        if job.status is ExportStatus.FAILED and job.error_message:
            actions.append(
                el("span", job.error_message, class_="text-destructive text-xs")
            )
        if not actions:
            actions.append(el("span", "—", class_="text-muted-foreground"))

        progress = min(max(float(job.progress or 0.0), 0.0), 100.0)
        progress_cell = el(
            "td",
            el(
                "div",
                el("span", f"{progress:.0f}%", class_="tabular-nums"),
                el(
                    "div",
                    el(
                        "div",
                        class_="bg-primary h-1.5 rounded",
                        style=f"width:{progress:.0f}%",
                    ),
                    class_="bg-muted h-1.5 rounded w-24 overflow-hidden",
                    aria_hidden="true",
                ),
                class_="flex items-center gap-2",
            ),
            class_=cell,
        )

        return el(
            "tr",
            el("td", job.resource_name, class_=cell),
            el("td", str(job.format.value).upper(), class_=cell),
            el(
                "td",
                el("span", job.status.value, class_=f"{status_class} font-medium"),
                class_=cell,
            ),
            progress_cell,
            el(
                "td",
                f"{job.processed_records}/{job.total_records}",
                class_=cell,
            ),
            el("td", _human_size(job.file_size), class_=cell),
            el("td", _format_dt(job.created_at), class_=cell),
            el("td", *actions, class_=f"{cell} space-x-3"),
            data_job_id=job.job_id,
        )

    # -- POST /exports ------------------------------------------------------

    async def create(self, request: Request) -> Response:
        """Create an export job and start it in the background."""
        user = self._user(request)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)

        form = self._form_data(request)
        if form is None:
            try:
                form = await request.form()
            except Exception:  # noqa: BLE001 — malformed body
                return HTMLResponse("Invalid form submission", status_code=400)

        resource_name = str(form.get("resource", "") or "").strip()
        fmt_key = str(form.get("format", "csv") or "csv").strip().lower()

        resource = self._resources.get(resource_name)
        if resource is None:
            return HTMLResponse(
                f"Unknown resource: {resource_name or '(none)'}", status_code=400
            )
        file_format = EXPORT_PAGE_FORMATS.get(fmt_key)
        if file_format is None:
            return HTMLResponse(
                f"Unsupported export format: {fmt_key}", status_code=400
            )

        if not await self._can_create(user, resource_name):
            return HTMLResponse("Forbidden", status_code=403)

        data_source = self._resolve_data_source(resource)
        if data_source is None:
            return HTMLResponse(
                "Export is unavailable for this resource", status_code=503
            )

        from lexigram.admin.data.adapters.export_adapter import (
            ExportDataSourceAdapter,
        )

        job_id = self._service.create_job(
            resource_name=resource_name,
            file_format=file_format,
            user_id=requester_id(user),
        )
        await self._service.start_background_export(
            job_id, ExportDataSourceAdapter(data_source)
        )
        logger.info(
            "admin.export_center.job_started",
            job_id=job_id,
            resource=resource_name,
            file_format=fmt_key,
        )
        return RedirectResponse(url=f"{self._prefix}/exports", status_code=303)

    @staticmethod
    def _resolve_data_source(resource: Any) -> Any | None:
        try:
            from lexigram.admin.resources.data_access import (
                get_resource_data_source,
            )

            return get_resource_data_source(resource)
        except Exception:  # noqa: BLE001 — duck-typed resources
            return getattr(resource, "_data_source", None)

    # -- POST /exports/{job_id}/cancel ---------------------------------------

    async def cancel(self, request: Request) -> Response:
        """Cancel a pending/processing export job (owner or superuser)."""
        user = self._user(request)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)

        job_id = str(request.path_params.get("job_id", ""))
        job = self._service.get_job(job_id)
        if job is None:
            return PlainTextResponse("Export job not found", status_code=404)
        if not may_access_job(user, job):
            return PlainTextResponse("Forbidden", status_code=403)

        self._service.cancel_job(job_id)
        logger.info("admin.export_center.job_cancelled", job_id=job_id)
        return RedirectResponse(url=f"{self._prefix}/exports", status_code=303)


__all__ = ["EXPORT_PAGE_FORMATS", "ExportCenter"]
