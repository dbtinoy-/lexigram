"""R30 regressions — export center (jobs page, create, cancel).

Covers:

* page — auth, empty state, owner-vs-superuser visibility, download link
  only on COMPLETED rows, cancel form only on PENDING/PROCESSING rows;
* create — unknown resource/format 400, permission matrix (permission
  service allow/deny, superuser-only fallback), job ownership + background
  start, 303 redirect;
* cancel — auth/404/ownership matrix, job transitions to CANCELLED.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.services.export.fallbacks import (
    InlineTaskRunner,
    LocalExportBlobStore,
)
from lexigram.admin.services.export.pages import (
    EXPORT_PAGE_FORMATS,
    ExportCenter,
    _human_size,
)
from lexigram.admin.services.export.scheduler import ExportFormat, ExportStatus
from lexigram.admin.services.export.service import ExportService


class _StubRenderer:
    """Captures render_page calls and returns a passthrough response."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def render_page(self, content, request=None, title="", breadcrumbs=None, **kw):
        from starlette.responses import HTMLResponse

        self.calls.append({"content": str(content), "title": title})
        return HTMLResponse(str(content))


class _FakeItems:
    """Minimal data-source resource for create tests."""

    def __init__(self) -> None:
        self._data_source = _FakeDataSource()


class _FakeDataSource:
    async def find_many(self, query):
        return SimpleNamespace(items=[{"id": 1, "name": "Widget"}])

    async def count(self, query=None):
        return 1


class _AllowPermissions:
    def __init__(self, allow: bool) -> None:
        self.allow = allow
        self.calls: list[tuple[Any, str]] = []

    async def can_list(self, user: Any, resource_name: str) -> bool:
        self.calls.append((user, resource_name))
        return self.allow


def make_user(user_id: Any = "u1", *, superuser: bool = False) -> Any:
    return SimpleNamespace(user_id=user_id, is_superuser=superuser)


def make_request(
    user: Any,
    *,
    form: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> Any:
    form_obj = None
    if form is not None:
        form_obj = SimpleNamespace(get=lambda k, d=None: form.get(k, d))
    scope: dict[str, Any] = {}
    if form_obj is not None:
        scope["admin_form_data"] = form_obj
    return SimpleNamespace(
        state=SimpleNamespace(user=user, csrf_token="tok"),
        path_params={"job_id": job_id} if job_id else {},
        scope=scope,
        session={},
    )


def make_center(
    tmp_path,
    *,
    resources: dict[str, Any] | None = None,
    permission_service: Any = None,
) -> tuple[ExportCenter, ExportService, _StubRenderer]:
    service = ExportService(
        storage=LocalExportBlobStore(tmp_path / "blobs"),
        task_manager=InlineTaskRunner(),
        download_url_prefix="/admin",
    )
    renderer = _StubRenderer()
    center = ExportCenter(
        export_service=service,
        resources=resources if resources is not None else {"items": _FakeItems()},
        config=SimpleNamespace(prefix="/admin"),
        renderer=renderer,
        permission_service=permission_service,
    )
    return center, service, renderer


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


class TestExportsPage:
    @pytest.mark.asyncio
    async def test_unauthenticated_401(self, tmp_path):
        center, _, _ = make_center(tmp_path)
        resp = await center.page(make_request(None))
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_state_rendered(self, tmp_path):
        center, _, renderer = make_center(tmp_path)
        resp = await center.page(make_request(make_user(superuser=True)))
        assert resp.status_code == 200
        assert "No export jobs yet" in renderer.calls[0]["content"]
        assert renderer.calls[0]["title"] == "Exports"

    @pytest.mark.asyncio
    async def test_superuser_sees_all_jobs_others_only_own(self, tmp_path):
        center, service, renderer = make_center(tmp_path)
        service.create_job("items", ExportFormat.CSV, user_id="u1")
        service.create_job("items", ExportFormat.CSV, user_id="someone-else")

        await center.page(make_request(make_user("root", superuser=True)))
        superuser_html = renderer.calls[-1]["content"]
        assert superuser_html.count("<tr data-job-id=") == 2

        await center.page(make_request(make_user("u1")))
        owner_html = renderer.calls[-1]["content"]
        assert owner_html.count("<tr data-job-id=") == 1

    @pytest.mark.asyncio
    async def test_completed_job_has_download_link_pending_has_cancel(self, tmp_path):
        center, service, renderer = make_center(tmp_path)
        pending_id = service.create_job("items", ExportFormat.CSV, user_id="u1")
        done_id = service.create_job("items", ExportFormat.CSV, user_id="u1")
        done = service.get_job(done_id)
        done.status = ExportStatus.COMPLETED
        done.download_url = f"/admin/exports/{done_id}/download"

        await center.page(make_request(make_user("u1")))
        html = renderer.calls[-1]["content"]
        assert f"/admin/exports/{done_id}/download" in html
        assert f"/admin/exports/{pending_id}/cancel" in html
        # The pending row must not link a download; the done row no cancel.
        assert f"/admin/exports/{pending_id}/download" not in html
        assert f"/admin/exports/{done_id}/cancel" not in html

    @pytest.mark.asyncio
    async def test_non_superuser_without_permissions_sees_no_form(self, tmp_path):
        center, _, renderer = make_center(tmp_path)  # no permission service
        await center.page(make_request(make_user("u1")))
        html = renderer.calls[-1]["content"]
        assert "do not have permission to start exports" in html
        assert "Start export" not in html


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreateExport:
    @pytest.mark.asyncio
    async def test_unknown_resource_400(self, tmp_path):
        center, _, _ = make_center(tmp_path)
        req = make_request(
            make_user(superuser=True), form={"resource": "nope", "format": "csv"}
        )
        assert (await center.create(req)).status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_format_400(self, tmp_path):
        center, _, _ = make_center(tmp_path)
        req = make_request(
            make_user(superuser=True), form={"resource": "items", "format": "pdf"}
        )
        assert (await center.create(req)).status_code == 400

    @pytest.mark.asyncio
    async def test_superuser_fallback_blocks_non_superuser(self, tmp_path):
        center, _, _ = make_center(tmp_path)  # no permission service
        req = make_request(make_user("u1"), form={"resource": "items"})
        assert (await center.create(req)).status_code == 403

    @pytest.mark.asyncio
    async def test_permission_service_denial_403(self, tmp_path):
        center, _, _ = make_center(
            tmp_path, permission_service=_AllowPermissions(False)
        )
        req = make_request(
            make_user(superuser=True), form={"resource": "items", "format": "csv"}
        )
        # Even a superuser goes through the permission service when present.
        assert (await center.create(req)).status_code == 403

    @pytest.mark.asyncio
    async def test_creates_owned_job_and_redirects(self, tmp_path):
        perms = _AllowPermissions(True)
        center, service, _ = make_center(tmp_path, permission_service=perms)
        req = make_request(
            make_user("u1"), form={"resource": "items", "format": "xlsx"}
        )
        resp = await center.create(req)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/admin/exports"

        jobs = service.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].user_id == "u1"
        assert jobs[0].format is ExportFormat.EXCEL
        assert perms.calls[-1][1] == "items"

    @pytest.mark.asyncio
    async def test_background_export_completes(self, tmp_path):
        import asyncio

        center, service, _ = make_center(
            tmp_path, permission_service=_AllowPermissions(True)
        )
        req = make_request(make_user("u1"), form={"resource": "items"})
        resp = await center.create(req)
        assert resp.status_code == 303

        # InlineTaskRunner executes on the running loop; yield until done.
        for _ in range(50):
            await asyncio.sleep(0.01)
            job = service.list_jobs()[0]
            if job.status in (ExportStatus.COMPLETED, ExportStatus.FAILED):
                break
        assert job.status is ExportStatus.COMPLETED
        assert job.download_url.endswith(f"/exports/{job.job_id}/download")
        assert await service.storage.exists(job.file_path) is True


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


class TestCancelExport:
    @pytest.mark.asyncio
    async def test_matrix(self, tmp_path):
        center, service, _ = make_center(tmp_path)
        job_id = service.create_job("items", ExportFormat.CSV, user_id="u1")

        # 401 unauthenticated
        resp = await center.cancel(make_request(None, job_id=job_id))
        assert resp.status_code == 401
        # 404 unknown
        resp = await center.cancel(make_request(make_user("u1"), job_id="nope"))
        assert resp.status_code == 404
        # 403 not owner
        resp = await center.cancel(make_request(make_user("mallory"), job_id=job_id))
        assert resp.status_code == 403
        # owner cancels → 303 + CANCELLED
        resp = await center.cancel(make_request(make_user("u1"), job_id=job_id))
        assert resp.status_code == 303
        assert service.get_job(job_id).status is ExportStatus.CANCELLED


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_human_size(self):
        assert _human_size(0) == "—"
        assert _human_size(None) == "—"
        assert _human_size(512) == "512 B"
        assert _human_size(2048) == "2.0 KB"
        assert _human_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_allowlist_excludes_pdf(self):
        assert set(EXPORT_PAGE_FORMATS) == {"csv", "json", "xlsx"}
