"""Download route for completed export jobs (B30).

Builds the Starlette handler mounted at ``{prefix}/exports/{job_id}/download``.
The URL is keyed by the opaque job id (uuid4) — never by a storage path —
and the handler enforces, fail-closed and in order:

1. **401** — no authenticated user on the request.
2. **404** — unknown job id.
3. **403** — requester is not the job owner (superuser bypass; jobs created
   without an owner are superuser-only).
4. **409** — job not ``COMPLETED`` yet (or no file recorded).
5. **410** — job completed but the artifact is gone from storage
   (e.g. cleaned up past ``max_file_age_days``).

On success the artifact bytes are returned with the format's MIME type, an
``attachment`` disposition, and ``Cache-Control: no-store``.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from starlette.responses import PlainTextResponse, Response

from lexigram.admin.services.export.scheduler import ExportFormat, ExportStatus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request

    from lexigram.admin.services.export.scheduler import ExportJob
    from lexigram.admin.services.export.service import ExportService

logger = logging.getLogger(__name__)

_CONTENT_TYPES: dict[ExportFormat, str] = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.JSON: "application/json",
    ExportFormat.EXCEL: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    ExportFormat.PDF: "application/pdf",
}


def _requester_id(user: Any) -> str | None:
    """Extract a comparable user identifier from the request user."""
    for attr in ("user_id", "id"):
        value = getattr(user, attr, None)
        if value is not None and not callable(value):
            return str(value)
    return None


def _is_superuser(user: Any) -> bool:
    """Strict superuser check (``is True`` guards against mock truthiness)."""
    return getattr(user, "is_superuser", False) is True


def _may_download(user: Any, job: ExportJob) -> bool:
    """Return True when ``user`` owns the job or is a superuser."""
    if _is_superuser(user):
        return True
    if job.user_id is None:
        # Ownerless jobs are superuser-only: fail closed rather than
        # letting any authenticated user fetch an unattributed artifact.
        return False
    requester = _requester_id(user)
    return requester is not None and requester == str(job.user_id)


def _safe_filename(job: ExportJob) -> str:
    """Derive a Content-Disposition filename from the job, never the raw path."""
    name = PurePosixPath(str(job.file_path or "")).name
    if not name:
        suffix = job.format.value if job.format else "dat"
        name = f"{job.resource_name}_export_{job.job_id}.{suffix}"
    # Strip characters that could break the header or smuggle directives.
    return "".join(c for c in name if c.isalnum() or c in "._-") or "export.dat"


def build_export_download_handler(
    export_service: ExportService,
) -> Callable[[Request], Awaitable[Response]]:
    """Build the download handler bound to a specific :class:`ExportService`.

    Args:
        export_service: The DI-registered export service whose job manager
            and blob storage back the route.

    Returns:
        An async Starlette endpoint ``(request) -> Response``.
    """

    async def download_export(request: Request) -> Response:
        user = getattr(request.state, "user", None)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)

        job_id = str(request.path_params.get("job_id", ""))
        job = export_service.get_job(job_id)
        if job is None:
            return PlainTextResponse("Export job not found", status_code=404)

        if not _may_download(user, job):
            return PlainTextResponse("Forbidden", status_code=403)

        if job.status != ExportStatus.COMPLETED or not job.file_path:
            return PlainTextResponse(
                f"Export job is not ready for download (status: {job.status.value})",
                status_code=409,
            )

        try:
            payload = await export_service.storage.download(job.file_path)
        except (FileNotFoundError, OSError, ValueError) as exc:
            logger.warning(
                "Export artifact missing for job %s (%s): %s",
                job.job_id,
                job.file_path,
                exc,
            )
            return PlainTextResponse(
                "Export file is no longer available", status_code=410
            )

        media_type = _CONTENT_TYPES.get(job.format, "application/octet-stream")
        filename = _safe_filename(job)
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    return download_export


__all__ = ["build_export_download_handler"]
