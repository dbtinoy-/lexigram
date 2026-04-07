"""Tenant aggregate root with domain events.

A :class:`Tenant` is the top-level aggregate in the platform bounded context.
It encapsulates the lifecycle of a registered organisation: creation, active
operation, and suspension.

When the aggregate state changes, a corresponding :class:`DomainEvent` is
recorded via :meth:`~lexigram.domain.models.aggregate.AggregateRoot._record_event`
and later dispatched by the service layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from lexigram.contracts.domain.events import DomainEvent
from lexigram.domain.models.aggregate import AggregateRoot


class TenantStatus(StrEnum):
    """Lifecycle states for a :class:`Tenant`.

    The canonical transition sequence is::

        ACTIVE → SUSPENDED

    A tenant begins life as ``ACTIVE`` immediately upon creation.
    """

    ACTIVE = "active"
    SUSPENDED = "suspended"


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TenantCreated(DomainEvent):
    """Emitted when a new tenant is successfully provisioned.

    Attributes:
        tenant_id: Unique identifier of the newly created tenant.
        name: Human-readable tenant name.
        slug: URL-safe unique identifier.
    """

    tenant_id: str = ""
    name: str = ""
    slug: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise event to a plain dictionary.

        Returns:
            Dictionary including base event fields plus tenant-specific data.
        """
        return {
            **super().to_dict(),
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
        }


@dataclass(frozen=True)
class TenantSuspended(DomainEvent):
    """Emitted when a tenant's account is suspended.

    Attributes:
        tenant_id: Unique identifier of the suspended tenant.
        reason: Human-readable suspension reason.
    """

    tenant_id: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise event to a plain dictionary.

        Returns:
            Dictionary including base event fields plus suspension-specific data.
        """
        return {
            **super().to_dict(),
            "tenant_id": self.tenant_id,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


@dataclass
class Tenant(AggregateRoot):
    """Aggregate root representing a registered organisation (tenant).

    Invariants enforced by this class:
    - A tenant cannot be suspended twice.
    - A suspended tenant cannot be re-activated via ``suspend``; a separate
      ``reactivate`` operation (not shown) would be needed.

    Attributes:
        id: Globally unique tenant identifier (UUID4 string).
        name: Human-readable display name.
        slug: URL-safe, lowercase, hyphen-separated identifier (must be unique).
        status: Current lifecycle status.
        created_at: UTC timestamp when the tenant was provisioned.
        suspended_at: UTC timestamp when the tenant was suspended, or ``None``.
    """

    name: str = ""
    slug: str = ""
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    suspended_at: datetime | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str, slug: str) -> Tenant:
        """Create a new active tenant and record a :class:`TenantCreated` event.

        Args:
            name: Human-readable display name.
            slug: URL-safe unique identifier.

        Returns:
            A new :class:`Tenant` instance with the creation event buffered.
        """
        tenant = cls(id=str(uuid.uuid4()), name=name, slug=slug)
        tenant._record_event(
            TenantCreated(
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
            )
        )
        return tenant

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def suspend(self, reason: str = "") -> None:
        """Suspend this tenant, preventing further logins and operations.

        Args:
            reason: Human-readable explanation for the suspension.

        Raises:
            ValueError: If the tenant is already suspended.
        """
        if self.status == TenantStatus.SUSPENDED:
            raise ValueError(
                f"Tenant {self.id!r} is already suspended."
            )
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = datetime.now(UTC)
        self._record_event(
            TenantSuspended(
                tenant_id=self.id,
                reason=reason,
            )
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the tenant is in the ``ACTIVE`` state."""
        return self.status == TenantStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"Tenant(id={self.id!r}, slug={self.slug!r}, status={self.status!r})"
        )


__all__ = [
    "Tenant",
    "TenantCreated",
    "TenantStatus",
    "TenantSuspended",
]
