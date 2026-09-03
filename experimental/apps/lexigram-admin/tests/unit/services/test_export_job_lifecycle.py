"""R28 (B30) regressions — job-based export lifecycle.

Covers the pieces that turn ExportService from dead infrastructure into a
working flow:

* ``LocalExportBlobStore`` — filesystem fallback blob store (round-trip,
  metadata, traversal guard).
* ``InlineTaskRunner`` — asyncio-backed TaskManagerProtocol fallback.
* ``ExportService`` fixes — real ``_get_file_size`` via ``storage.info``
  and job-id-keyed ``_generate_download_url``.
* Download route handler — fail-closed auth/ownership/status matrix.
* ``AdminExportSubProvider`` — DI registration + boot-time upgrades.
* ``_mount_export_download`` — route mounting step.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.services.export.download import build_export_download_handler
from lexigram.admin.services.export.fallbacks import (
    InlineTaskRunner,
    LocalExportBlobStore,
)
from lexigram.admin.services.export.scheduler import ExportFormat, ExportStatus
from lexigram.admin.services.export.service import ExportService


class FakeDataSource:
    """Two-row data source implementing the export protocol surface."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or [
            {"id": 1, "name": "Widget"},
            {"id": 2, "name": "Gadget"},
        ]

    async def get_export_count(self, filters: dict[str, Any]) -> int:
        return len(self.rows)

    async def get_export_data(
        self,
        filters: dict[str, Any],
        columns: list[str],
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        start = offset or 0
        end = start + (limit or len(self.rows))
        return self.rows[start:end]

    async def get_column_definitions(self) -> list[Any]:
        return []


def make_service(tmp_path, **kwargs) -> ExportService:
    return ExportService(
        storage=LocalExportBlobStore(tmp_path / "blobs"),
        task_manager=InlineTaskRunner(),
        **kwargs,
    )


def make_request(user: Any, job_id: str) -> Any:
    """Minimal request stub: handler reads .state.user and .path_params."""
    return SimpleNamespace(
        state=SimpleNamespace(user=user),
        path_params={"job_id": job_id},
    )


def make_user(user_id: Any = "u1", *, superuser: bool = False) -> Any:
    return SimpleNamespace(user_id=user_id, is_superuser=superuser)


# ---------------------------------------------------------------------------
# LocalExportBlobStore
# ---------------------------------------------------------------------------


class TestLocalExportBlobStore:
    @pytest.mark.asyncio
    async def test_upload_download_roundtrip(self, tmp_path):
        store = LocalExportBlobStore(tmp_path)
        info = await store.upload("exports/a.csv", b"x,y\n1,2\n")
        assert info.size == 8
        assert await store.download("exports/a.csv") == b"x,y\n1,2\n"
        assert await store.exists("exports/a.csv") is True

    @pytest.mark.asyncio
    async def test_str_payload_encoded_utf8(self, tmp_path):
        store = LocalExportBlobStore(tmp_path)
        await store.upload("s.txt", "héllo")
        assert await store.download("s.txt") == "héllo".encode()

    @pytest.mark.asyncio
    async def test_info_reports_size_and_missing_raises(self, tmp_path):
        store = LocalExportBlobStore(tmp_path)
        await store.upload("f.json", b"{}")
        info = await store.info("f.json")
        assert info.size == 2
        with pytest.raises(FileNotFoundError):
            await store.info("missing.json")

    @pytest.mark.asyncio
    async def test_traversal_guard(self, tmp_path):
        store = LocalExportBlobStore(tmp_path / "root")
        with pytest.raises(ValueError, match="escapes"):
            await store.upload("../outside.txt", b"nope")
        with pytest.raises(ValueError, match="escapes"):
            await store.download("../../etc/passwd")
        assert await store.exists("../../etc/passwd") is False

    @pytest.mark.asyncio
    async def test_delete_missing_is_noop(self, tmp_path):
        store = LocalExportBlobStore(tmp_path)
        await store.delete("never-existed.bin")  # must not raise
        await store.upload("x.bin", b"1")
        await store.delete("x.bin")
        assert await store.exists("x.bin") is False

    @pytest.mark.asyncio
    async def test_stream_and_list(self, tmp_path):
        store = LocalExportBlobStore(tmp_path)
        await store.upload("dir/a.csv", b"abcdef")
        chunks = [c async for c in store.stream("dir/a.csv", chunk_size=4)]
        assert chunks == [b"abcd", b"ef"]
        listed = [i.path async for i in store.list()]
        assert listed == ["dir/a.csv"]

    @pytest.mark.asyncio
    async def test_protocol_capabilities_are_honest(self, tmp_path):
        from lexigram.contracts.core import HealthStatus
        from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol

        store = LocalExportBlobStore(tmp_path)
        assert isinstance(store, BlobStoreProtocol)
        await store.upload("artifact.csv", b"data")
        assert (await store.get_url("artifact.csv")).startswith("file://")
        health = await store.health_check()
        assert health.status is HealthStatus.HEALTHY
        with pytest.raises(NotImplementedError, match="no presigned URLs"):
            await store.get_presigned_url("artifact.csv")


# ---------------------------------------------------------------------------
# InlineTaskRunner
# ---------------------------------------------------------------------------


class TestInlineTaskRunner:
    @pytest.mark.asyncio
    async def test_background_task_runs_and_untracks(self):
        runner = InlineTaskRunner()
        ran = asyncio.Event()

        async def work():
            ran.set()

        task = runner.create_background_task(work(), name="t1")
        await asyncio.wait_for(task, timeout=2)
        assert ran.is_set()
        assert runner.get_task_counts() == {"background": 0, "critical": 0}

    @pytest.mark.asyncio
    async def test_shutdown_cancels_pending_background(self):
        runner = InlineTaskRunner()

        async def forever():
            await asyncio.sleep(3600)

        task = runner.create_background_task(forever())
        assert runner.get_task_counts()["background"] == 1
        await runner.shutdown_gracefully(background_timeout=1)
        assert task.cancelled() or task.done()


# ---------------------------------------------------------------------------
# ExportService placeholder fixes
# ---------------------------------------------------------------------------


class TestServiceLifecycle:
    @pytest.mark.asyncio
    async def test_completed_job_gets_real_size_and_job_id_url(self, tmp_path):
        service = make_service(tmp_path, download_url_prefix="/panel")
        job_id = service.create_job("products", ExportFormat.CSV, user_id="u1")
        result = await service.execute_export(job_id, FakeDataSource())
        assert result.is_ok()

        job = service.get_job(job_id)
        assert job.status is ExportStatus.COMPLETED
        assert job.file_size > 0
        assert job.download_url == f"/panel/exports/{job_id}/download"
        # URL must not leak the storage path
        assert job.file_path not in job.download_url
        # Artifact really exists in storage
        assert await service.storage.exists(job.file_path) is True

    @pytest.mark.asyncio
    async def test_default_prefix_and_trailing_slash_normalized(self, tmp_path):
        assert make_service(tmp_path).download_url_prefix == "/admin"
        svc = make_service(tmp_path, download_url_prefix="/admin/")
        assert svc.download_url_prefix == "/admin"

    @pytest.mark.asyncio
    async def test_get_file_size_fails_soft(self, tmp_path):
        service = make_service(tmp_path)
        assert await service._get_file_size("does/not/exist.csv") == 0


# ---------------------------------------------------------------------------
# Download route handler
# ---------------------------------------------------------------------------


@pytest.fixture
def completed_setup(tmp_path):
    """Service with one COMPLETED csv job owned by 'u1'."""

    async def build():
        service = make_service(tmp_path)
        job_id = service.create_job("products", ExportFormat.CSV, user_id="u1")
        result = await service.execute_export(job_id, FakeDataSource())
        assert result.is_ok()
        return service, job_id

    return build


class TestDownloadHandler:
    @pytest.mark.asyncio
    async def test_unauthenticated_401(self, completed_setup):
        service, job_id = await completed_setup()
        handler = build_export_download_handler(service)
        resp = await handler(make_request(None, job_id))
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_job_404(self, tmp_path):
        handler = build_export_download_handler(make_service(tmp_path))
        resp = await handler(make_request(make_user(), "nope"))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_owner_403(self, completed_setup):
        service, job_id = await completed_setup()
        handler = build_export_download_handler(service)
        resp = await handler(make_request(make_user("intruder"), job_id))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ownerless_job_requires_superuser(self, tmp_path):
        service = make_service(tmp_path)
        job_id = service.create_job("products", ExportFormat.CSV)  # no user_id
        await service.execute_export(job_id, FakeDataSource())
        handler = build_export_download_handler(service)
        assert (await handler(make_request(make_user("u1"), job_id))).status_code == 403
        ok = await handler(make_request(make_user("root", superuser=True), job_id))
        assert ok.status_code == 200

    @pytest.mark.asyncio
    async def test_superuser_bypasses_ownership(self, completed_setup):
        service, job_id = await completed_setup()
        handler = build_export_download_handler(service)
        resp = await handler(make_request(make_user("other", superuser=True), job_id))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pending_job_409(self, tmp_path):
        service = make_service(tmp_path)
        job_id = service.create_job("products", ExportFormat.CSV, user_id="u1")
        handler = build_export_download_handler(service)
        resp = await handler(make_request(make_user(), job_id))
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_missing_artifact_410(self, completed_setup):
        service, job_id = await completed_setup()
        job = service.get_job(job_id)
        await service.storage.delete(job.file_path)
        handler = build_export_download_handler(service)
        resp = await handler(make_request(make_user(), job_id))
        assert resp.status_code == 410

    @pytest.mark.asyncio
    async def test_owner_downloads_csv_with_headers(self, completed_setup):
        service, job_id = await completed_setup()
        handler = build_export_download_handler(service)
        resp = await handler(make_request(make_user(), job_id))
        assert resp.status_code == 200
        assert b"Widget" in resp.body
        assert resp.headers["content-type"].startswith("text/csv")
        disposition = resp.headers["content-disposition"]
        assert disposition.startswith('attachment; filename="')
        assert ".csv" in disposition
        assert resp.headers["cache-control"] == "no-store"

    @pytest.mark.asyncio
    async def test_user_with_plain_id_attribute_matches(self, completed_setup):
        service, job_id = await completed_setup()
        handler = build_export_download_handler(service)
        user = SimpleNamespace(id="u1", is_superuser=False)
        resp = await handler(make_request(user, job_id))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# DI sub-provider + route mounting
# ---------------------------------------------------------------------------


class FakeContainer:
    def __init__(self) -> None:
        self.singletons: dict[Any, Any] = {}

    def singleton(self, key: Any, value: Any) -> None:
        self.singletons[key] = value

    async def resolve(self, key: Any) -> Any:
        if key in self.singletons:
            return self.singletons[key]
        raise KeyError(key)


class TestSubProvider:
    @pytest.mark.asyncio
    async def test_register_binds_singleton_with_fallbacks(self):
        from lexigram.admin.di.sub_providers.export import AdminExportSubProvider

        provider = AdminExportSubProvider(config=SimpleNamespace(prefix="/panel"))
        container = FakeContainer()
        await provider.register(container)

        service = container.singletons[ExportService]
        assert isinstance(service.storage, LocalExportBlobStore)
        assert isinstance(service.task_manager, InlineTaskRunner)
        assert service.download_url_prefix == "/panel"

    @pytest.mark.asyncio
    async def test_boot_upgrades_storage_from_container(self, tmp_path):
        from lexigram.admin.di.sub_providers.export import AdminExportSubProvider
        from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol

        provider = AdminExportSubProvider(config=SimpleNamespace(prefix="/admin"))
        container = FakeContainer()
        await provider.register(container)

        host_store = LocalExportBlobStore(tmp_path / "host")
        container.singleton(BlobStoreProtocol, host_store)
        await provider.boot(container)
        assert provider.service.storage is host_store

    @pytest.mark.asyncio
    async def test_boot_keeps_fallbacks_when_host_provides_nothing(self):
        from lexigram.admin.di.sub_providers.export import AdminExportSubProvider

        provider = AdminExportSubProvider(config=SimpleNamespace(prefix="/admin"))
        container = FakeContainer()
        await provider.register(container)
        await provider.boot(container)  # nothing resolvable → no crash
        assert isinstance(provider.service.storage, LocalExportBlobStore)
        assert isinstance(provider.service.task_manager, InlineTaskRunner)


class TestMountStep:
    @pytest.mark.asyncio
    async def test_mount_registers_routes(self, tmp_path):
        from lexigram.admin.di.mount.contributors import AdminMountContributorsMixin

        recorded: list[tuple] = []

        class Router:
            def add_route(self, path, method, handler, name):
                recorded.append((path, method, handler, name))

        class Host(AdminMountContributorsMixin):
            _config = SimpleNamespace(prefix="/admin")

        container = FakeContainer()
        container.singleton(ExportService, make_service(tmp_path))

        class NavContributor:
            enabled_url: str | None = None

            def enable_export_center(self, url: str) -> None:
                self.enabled_url = url

        nav_contributor = NavContributor()
        ctx = SimpleNamespace(
            router=Router(), resources={}, contributors=[nav_contributor]
        )
        await Host()._mount_export_center(container, ctx)

        # R30: the export center registers page + create + cancel + download;
        # R32 adds the jobs fragment for HTMX polling.
        by_name = {name: (path, method) for path, method, _h, name in recorded}
        assert by_name["admin_exports_page"] == ("/exports", "GET")
        assert by_name["admin_exports_create"] == ("/exports", "POST")
        assert by_name["admin_exports_jobs"] == ("/exports/jobs", "GET")
        assert by_name["admin_exports_cancel"] == (
            "/exports/{job_id}/cancel",
            "POST",
        )
        assert by_name["admin_export_download"] == (
            "/exports/{job_id}/download",
            "GET",
        )
        assert len(recorded) == 5
        # R32: the sidebar hook fires only after successful registration.
        assert nav_contributor.enabled_url == "/admin/exports"

    @pytest.mark.asyncio
    async def test_mount_skips_when_service_unresolvable(self):
        from lexigram.admin.di.mount.contributors import AdminMountContributorsMixin

        class Router:
            def add_route(self, *a):  # pragma: no cover — must not be called
                raise AssertionError("route must not be registered")

        class Host(AdminMountContributorsMixin):
            _config = SimpleNamespace(prefix="/admin")

        ctx = SimpleNamespace(router=Router(), resources={})
        # Empty container → resolve raises → step logs and skips, no raise.
        await Host()._mount_export_center(FakeContainer(), ctx)
