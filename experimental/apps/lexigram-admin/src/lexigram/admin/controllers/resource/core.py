"""Core state and lifecycle for the resource controller."""

from __future__ import annotations

from typing import Any, Generic

from starlette.requests import Request

from lexigram.admin.controllers.resource.meta import ResourceMeta, T
from lexigram.admin.data.data_source import IDataSource as DataSourceProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class ResourceCoreMixin(Generic[T]):
    """Shared state, audit, and revisions."""

    meta: ResourceMeta

    _data_source: DataSourceProtocol[T] | None
    _audit_logger: Any
    _revision_service: Any

    # When True, DELETE calls soft-delete (sets deleted_at) instead of hard-delete.
    # Use RepositoryDataSource(soft_delete_enabled=True) to filter them in queries.
    soft_delete_enabled: bool = False

    def __init__(
        self,
        data_source: DataSourceProtocol[T] | None = None,
        meta: ResourceMeta | None = None,
    ):
        self._data_source = data_source
        if meta:
            self.meta = meta
        # Optional audit logger — set via set_audit_logger() or DI
        self._audit_logger: Any = None
        # Optional revision service — set via set_revision_service() or DI
        self._revision_service: Any = None

    def set_audit_logger(self, audit_logger: Any) -> None:
        """Attach an audit logger for CRUD event tracking.

        Args:
            audit_logger: Any object implementing ``async log(AuditEntry) -> None``.
        """
        self._audit_logger = audit_logger

    def set_revision_service(self, revision_service: Any) -> None:
        """Attach a :class:`~lexigram.admin.services.revisions.RevisionService`.

        When set, a snapshot is recorded after every successful create or
        update. The service also exposes ``diff`` and ``revert_data`` for the
        revision history UI.

        Args:
            revision_service: ``RevisionService`` instance.
        """
        self._revision_service = revision_service

    async def _record_revision(
        self,
        request: Request,
        resource_id: str,
        data: dict[str, Any],
        comment: str = "",
    ) -> None:
        """Silently create a revision snapshot if a service is attached.

        Args:
            request: Current HTTP request (actor identity extracted from state).
            resource_id: Record identifier.
            data: Full field snapshot to persist.
            comment: Optional human-readable description.
        """
        if self._revision_service is None:
            return
        try:
            user = getattr(request.state, "user", None)
            actor_id = str(getattr(user, "id", getattr(user, "user_id", "system")))
            resource_name = getattr(self.meta, "name", "resource")
            await self._revision_service.record(
                resource_name,
                resource_id,
                data,
                actor_id=actor_id,
                comment=comment,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Revision recording failed for resource %s/%s",
                getattr(self.meta, "name", ""),
                resource_id,
            )

    async def _emit_audit(
        self,
        request: Request,
        action: str,
        item_id: str = "",
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        outcome: str = "success",
    ) -> None:
        """Emit an audit log entry if a logger is attached.

        Args:
            request: Current HTTP request (used for actor identity and metadata).
            action: Machine-readable action (e.g. ``"user.create"``).
            item_id: Identifier of the affected record.
            old_values: Field snapshot before the change.
            new_values: Field snapshot after the change.
            outcome: ``"success"`` or ``"failure"``.
        """
        if self._audit_logger is None:
            return
        try:
            from lexigram.contracts.audit import AuditEntry

            user = getattr(request.state, "user", None)
            actor_id = str(getattr(user, "id", getattr(user, "user_id", "anonymous")))
            resource_name = getattr(self.meta, "name", "unknown")
            entry = AuditEntry(
                action=action,
                actor_id=actor_id,
                resource_type=resource_name,
                resource_id=str(item_id),
                outcome=outcome,
                old_values=old_values,
                new_values=new_values,
                metadata={
                    "ip": request.client.host if request.client else "",
                    "user_agent": request.headers.get("user-agent", ""),
                    "path": str(request.url),
                },
            )
            await self._audit_logger.log(entry)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Audit logging failed for action %s on %s/%s",
                action,
                getattr(self.meta, "name", ""),
                item_id,
            )

    def get_data_source(self) -> DataSourceProtocol[T]:
        """Get the data source for this resource."""
        if self._data_source is None:
            raise NotImplementedError("Subclass must implement get_data_source()")
        return self._data_source
