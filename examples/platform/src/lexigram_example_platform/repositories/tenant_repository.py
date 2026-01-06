"""Tenant repository protocol and in-memory implementation.

The :class:`TenantRepositoryProtocol` defines the persistence contract for
:class:`~lexigram_example_platform.domain.tenant.Tenant` aggregates.
The :class:`InMemoryTenantRepository` provides a test-friendly, zero-dependency
implementation suitable for unit tests and local development.

In production, replace the in-memory implementation with a SQL-backed one
(``lexigram-sql``) without changing any service code — the protocol is the
only coupling point.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram_example_platform.domain.tenant import Tenant


@runtime_checkable
class TenantRepositoryProtocol(Protocol):
    """Persistence contract for :class:`Tenant` aggregates.

    All methods are ``async`` because production implementations will issue
    I/O operations (SQL queries, HTTP calls, etc.).
    """

    async def get(self, tenant_id: str) -> Tenant | None:
        """Fetch a tenant by its unique identifier.

        Args:
            tenant_id: UUID string of the tenant to retrieve.

        Returns:
            The :class:`Tenant` if found, otherwise ``None``.
        """
        ...

    async def find_by_slug(self, slug: str) -> Tenant | None:
        """Fetch a tenant by its URL-safe slug.

        Args:
            slug: Unique slug to look up.

        Returns:
            The :class:`Tenant` if found, otherwise ``None``.
        """
        ...

    async def save(self, tenant: Tenant) -> None:
        """Persist a tenant aggregate (insert or update).

        Args:
            tenant: The aggregate to persist.
        """
        ...

    async def list_all(self) -> list[Tenant]:
        """Return all stored tenants.

        Returns:
            Unordered list of every :class:`Tenant` in the store.
        """
        ...


class InMemoryTenantRepository:
    """In-memory :class:`TenantRepositoryProtocol` implementation.

    Stores tenants in a plain ``dict`` keyed by ``tenant.id``.  Suitable
    for unit tests and local development — not thread-safe and not
    persistent across process restarts.
    """

    def __init__(self) -> None:
        self._store: dict[str, Tenant] = {}

    async def get(self, tenant_id: str) -> Tenant | None:
        """Fetch a tenant by its unique identifier.

        Args:
            tenant_id: UUID string of the tenant to retrieve.

        Returns:
            The :class:`Tenant` if found, otherwise ``None``.
        """
        return self._store.get(tenant_id)

    async def find_by_slug(self, slug: str) -> Tenant | None:
        """Fetch a tenant by its URL-safe slug.

        Args:
            slug: Unique slug to look up.

        Returns:
            The :class:`Tenant` if found, otherwise ``None``.
        """
        for tenant in self._store.values():
            if tenant.slug == slug:
                return tenant
        return None

    async def save(self, tenant: Tenant) -> None:
        """Persist a tenant aggregate (insert or update).

        Args:
            tenant: The aggregate to persist.
        """
        self._store[tenant.id] = tenant

    async def list_all(self) -> list[Tenant]:
        """Return all stored tenants.

        Returns:
            Unordered list of every :class:`Tenant` in the store.
        """
        return list(self._store.values())


__all__ = [
    "InMemoryTenantRepository",
    "TenantRepositoryProtocol",
]
