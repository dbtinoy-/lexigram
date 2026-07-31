"""Admin panel contributor for audit log management."""

from __future__ import annotations

from collections.abc import Sequence
import csv
import io
from typing import TYPE_CHECKING, Any

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.types import (
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
)
from lexigram.contracts.audit import AuditLoggerProtocol, AuditQuery
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditEntry, AuditVerifierProtocol
    from lexigram.contracts.core.di import ContainerResolverProtocol

logger = get_logger(__name__)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Audit",
        url="/admin/audit",
        icon="shield-check",
        group="security",
        order=45,
        children=(
            NavigationContribution(
                label="Audit Log",
                url="/admin/audit",
                icon="shield-check",
                group="security",
                order=10,
            ),
            NavigationContribution(
                label="Verification",
                url="/admin/audit/verification",
                icon="shield-check",
                group="security",
                order=20,
            ),
        ),
    ),
)


class AuditAdminContributor(BaseAdminContributor):
    """Admin panel contributor for audit log management.

    Registered via ``lexigram.admin.contributors`` entry point.
    Provides audit log search, filter, export, and verification status.
    Dependencies are resolved from the container in ``on_admin_boot``.
    """

    name = "audit"
    display_name = "Audit Trail"
    icon = "shield-check"
    group = "security"
    priority = 45

    def __init__(self) -> None:
        self._logger: AuditLoggerProtocol | None = None
        self._verifier: AuditVerifierProtocol | None = None

    async def on_admin_boot(self, container: ContainerResolverProtocol | None) -> None:
        """Resolve audit dependencies from the DI container.

        Args:
            container: The DI container resolver.
        """
        if container is None:
            return
        try:
            self._logger = await container.resolve(AuditLoggerProtocol)
        except Exception:  # noqa: BLE001
            logger.warning("audit_contributor.logger_unavailable")
        try:
            from lexigram.contracts.audit import (
                AuditVerifierProtocol as _AuditVerifierProtocol,  # noqa: PLC0415
            )

            self._verifier = await container.resolve(_AuditVerifierProtocol)
        except Exception:  # noqa: BLE001, S110
            pass  # verifier is optional

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        """Return the navigation items for this contributor."""
        return list(_NAV_ITEMS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        """Return the management page definitions for this contributor."""
        return [
            ManagementPageDefinition(
                name="audit_log",
                title="Audit Log",
                contributor="audit",
                route_path="/audit",
                handler="lexigram.audit.admin.pages.audit_log:AuditLogPage",
                category=PageCategory.SECURITY,
                icon="shield-check",
                description="Search and browse audit log entries",
                order=10,
            ),
            ManagementPageDefinition(
                name="audit_verification",
                title="Audit Verification",
                contributor="audit",
                route_path="/audit/verification",
                handler="lexigram.audit.admin.pages.verification:AuditVerificationPage",
                category=PageCategory.SECURITY,
                icon="shield-check",
                description="Verify audit log integrity",
                order=20,
            ),
        ]

    async def search(self, query: AuditQuery) -> list[AuditEntry]:
        """Search audit entries by query filters.

        Args:
            query: Filter criteria.

        Returns:
            Matching audit entries, newest-first.
        """
        if self._logger is None:
            return []
        return await self._logger.query(query)

    async def export(self, query: AuditQuery, format: str = "json") -> bytes:
        """Export filtered audit entries as JSON or CSV.

        Args:
            query: Filter criteria.
            format: ``"json"`` or ``"csv"``.

        Returns:
            Encoded bytes of the export.
        """
        if self._logger is None:
            return b""
        entries = await self._logger.query(query)
        if format == "csv":
            return self._to_csv(entries)
        return dumps_str(
            [
                {
                    "action": e.action,
                    "actor_id": e.actor_id,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "outcome": e.outcome,
                    "severity": e.severity.value,
                    "occurred_at": e.occurred_at.isoformat(),
                    "source": e.source,
                    "tenant_id": e.tenant_id,
                    "metadata": e.metadata,
                }
                for e in entries
            ],
        ).encode("utf-8")

    async def verification_status(self) -> dict[str, Any]:
        """Return latest verification results.

        Returns:
            Dict with ``verified`` bool and ``mismatches`` count.
        """
        if self._verifier is not None:
            mismatches = await self._verifier.verify_recent()
            return {"verified": len(mismatches) == 0, "mismatches": len(mismatches)}
        return {"verified": None, "message": "Verifier not configured"}

    def _to_csv(self, entries: list[AuditEntry]) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "action",
                "actor_id",
                "resource_type",
                "resource_id",
                "outcome",
                "severity",
                "occurred_at",
                "source",
                "tenant_id",
            ]
        )
        for e in entries:
            writer.writerow(
                [
                    e.action,
                    e.actor_id,
                    e.resource_type,
                    e.resource_id,
                    e.outcome,
                    e.severity.value,
                    e.occurred_at.isoformat(),
                    e.source,
                    e.tenant_id or "",
                ]
            )
        return buf.getvalue().encode("utf-8")
