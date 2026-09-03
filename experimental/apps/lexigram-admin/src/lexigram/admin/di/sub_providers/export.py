"""Admin export sub-provider — job-based export lifecycle wiring (B30).

Registers :class:`ExportService` as a container singleton so the async
export job flow (create job → background execution → download) is usable
out of the box:

* ``register()`` constructs the service with zero-config local fallbacks —
  :class:`LocalExportBlobStore` (filesystem artifacts under a dedicated
  temp directory) and :class:`InlineTaskRunner` (``asyncio``-backed task
  manager) — and a download-URL prefix derived from the admin mount prefix.
* ``boot()`` opportunistically upgrades individual dependencies from the
  container when a host application registers real implementations
  (``BlobStoreProtocol``, ``TaskManagerProtocol``, ``AuditLoggerProtocol``,
  ``MailerProtocol``). Absence of any of them is normal and non-fatal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.services.export.service import ExportService
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from lexigram.logging import get_logger

_log = get_logger(__name__)


class AdminExportSubProvider:
    """Wires the job-based export service into the admin DI bundle."""

    def __init__(self, config: AdminConfig) -> None:
        self._config = config
        self._service: ExportService | None = None

    @property
    def service(self) -> ExportService | None:
        """Return the constructed export service (None before register)."""
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Construct and bind the export service with local fallbacks."""
        from lexigram.admin.services.export.fallbacks import (
            InlineTaskRunner,
            LocalExportBlobStore,
        )
        from lexigram.admin.services.export.service import ExportService

        prefix = getattr(self._config, "prefix", None) or "/admin"
        service = ExportService(
            storage=LocalExportBlobStore(),
            task_manager=InlineTaskRunner(),
            download_url_prefix=prefix,
        )
        self._service = service
        container.singleton(ExportService, service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Upgrade fallback deps with host-provided implementations."""
        service = self._service
        if service is None:
            return

        from lexigram.contracts.core.concurrency_protocols import (
            TaskManagerProtocol,
        )
        from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol

        async def _try_resolve(protocol: Any) -> Any | None:
            try:
                return await container.resolve(protocol)
            except Exception:  # noqa: BLE001 — absence is expected
                return None

        storage = await _try_resolve(BlobStoreProtocol)
        if storage is not None and storage is not service.storage:
            service.storage = storage
            _log.info("admin.export.storage_upgraded", backend=type(storage).__name__)

        task_manager = await _try_resolve(TaskManagerProtocol)
        if task_manager is not None and task_manager is not service.task_manager:
            service.task_manager = task_manager

        if service.audit is None:
            from lexigram.contracts.audit import AuditLoggerProtocol

            service.audit = await _try_resolve(AuditLoggerProtocol)

        if service.messaging is None:
            from lexigram.contracts.mailer import MailerProtocol

            service.messaging = await _try_resolve(MailerProtocol)

    async def shutdown(self) -> None:
        """Cancel any in-flight background export tasks."""
        service = self._service
        self._service = None
        if service is None:
            return
        try:
            await service.task_manager.shutdown_gracefully()
        except Exception:  # noqa: BLE001 — best-effort cleanup
            _log.warning("admin.export.shutdown_failed", exc_info=True)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return export wiring health."""
        return HealthCheckResult(
            component="admin_export",
            status=HealthStatus.HEALTHY if self._service else HealthStatus.UNKNOWN,
            message="Export service ready" if self._service else "Not registered",
        )


__all__ = ["AdminExportSubProvider"]
