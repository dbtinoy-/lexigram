"""Admin resilience utilities.

Provides the transaction() context manager for CRUD operations (FWK-11)
and AuditRepositoryMixin (FWK-12).

Configuration types for circuit breaker, retry, and timeout policies live in
``lexigram.contracts.infra.resilience.models`` — import them from there.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from lexigram.contracts.admin.audit_logger import AdminAuditLoggerProtocol

if TYPE_CHECKING:
    from lexigram.contracts.data import UnitOfWorkProtocol

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Transaction Context Manager
# ============================================================================


@asynccontextmanager
async def transaction(
    uow: UnitOfWorkProtocol,
) -> AsyncGenerator[UnitOfWorkProtocol, None]:
    """Async context manager that wraps a :class:`UnitOfWorkProtocol` boundary.

    The ``UnitOfWorkProtocol`` is responsible for beginning the transaction on
    ``__aenter__`` and rolling back on any unhandled exception in
    ``__aexit__``.  This helper simply enters the UoW context and yields it so
    callers can work with repositories, then exits cleanly on success (commit)
    or failure (rollback) via the UoW's own ``__aexit__`` semantics.

    The ``uow`` **must** be injected via the DI container — never created ad
    hoc.  Callers obtain it via constructor injection from
    ``DatabaseProviderProtocol.get_unit_of_work()``.

    Args:
        uow: A :class:`~lexigram.contracts.data.UnitOfWorkProtocol` instance.

    Yields:
        The same ``uow`` instance so callers can access repositories.

    Example::

        class UserService:
            def __init__(self, db: DatabaseProviderProtocol) -> None:
                self._db = db

            async def create(self, data: dict) -> User:
                async with transaction(self._db.get_unit_of_work()) as uow:
                    user = User(**data)
                    uow.register_new(user)
                    await uow.commit()
                    return user
    """
    async with uow:
        yield uow


# ============================================================================
# Audit Mixin
# ============================================================================


@dataclass
class AuditEntry:
    """Audit log entry."""

    action: str
    resource_type: str
    resource_id: Any
    user_id: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    changes: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class InMemoryAuditLogger:
    """In-memory audit logger for development/testing."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Any,
        user_id: Any,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = AuditEntry(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            changes=changes,
            metadata=metadata,
        )
        self._entries.append(entry)

    def get_entries(
        self,
        resource_type: str | None = None,
        resource_id: Any | None = None,
        action: str | None = None,
    ) -> list[AuditEntry]:
        """Get audit entries with optional filtering."""
        entries = self._entries

        if resource_type:
            entries = list(filter(lambda e: e.resource_type == resource_type, entries))
        if resource_id:
            entries = list(filter(lambda e: e.resource_id == resource_id, entries))
        if action:
            entries = list(filter(lambda e: e.action == action, entries))

        return entries


class AuditRepositoryMixin(Generic[T]):
    """Mixin adding audit logging to repository operations.

    Add to your data source class to automatically log CRUD operations.

    Example:
        >>> class UserDataSource(AuditRepositoryMixin[User]):
        ...     resource_type = "users"
        ...
        ...     async def create(self, data: dict, user: Any) -> User:
        ...         result = await super().create(data, user)
        ...         await self._audit_create(result, user)
        ...         return result
    """

    resource_type: str = "unknown"
    _audit_logger: AdminAuditLoggerProtocol | None = None

    def set_audit_logger(self, logger: AdminAuditLoggerProtocol) -> None:
        """Set the audit logger."""
        self._audit_logger = logger

    async def _audit_create(self, record: T, user: Any) -> None:
        """Log a create operation."""
        if self._audit_logger:
            record_id = getattr(record, "id", None)
            user_id = getattr(user, "id", None) if user else None
            await self._audit_logger.log(
                action="create",
                resource_type=self.resource_type,
                resource_id=record_id,
                user_id=user_id,
                changes={"created": True},
            )

    async def _audit_update(
        self,
        record: T,
        changes: dict[str, Any],
        user: Any,
    ) -> None:
        """Log an update operation."""
        if self._audit_logger:
            record_id = getattr(record, "id", None)
            user_id = getattr(user, "id", None) if user else None
            await self._audit_logger.log(
                action="update",
                resource_type=self.resource_type,
                resource_id=record_id,
                user_id=user_id,
                changes=changes,
            )

    async def _audit_delete(self, record_id: Any, user: Any) -> None:
        """Log a delete operation."""
        if self._audit_logger:
            user_id = getattr(user, "id", None) if user else None
            await self._audit_logger.log(
                action="delete",
                resource_type=self.resource_type,
                resource_id=record_id,
                user_id=user_id,
            )

    async def _audit_bulk_action(
        self,
        action: str,
        record_ids: list[Any],
        user: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a bulk operation."""
        if self._audit_logger:
            user_id = getattr(user, "id", None) if user else None
            await self._audit_logger.log(
                action=f"bulk_{action}",
                resource_type=self.resource_type,
                resource_id=record_ids,
                user_id=user_id,
                metadata=metadata,
            )


__all__ = [
    "AdminAuditLoggerProtocol",
    "AuditEntry",
    # Audit
    "AuditRepositoryMixin",
    # Transaction context manager
    "InMemoryAuditLogger",
    "transaction",
]
