"""Membership repository protocol and in-memory implementation.

The :class:`MembershipRepositoryProtocol` defines the persistence contract for
:class:`~lexigram_example_platform.domain.membership.Membership` entities.
The :class:`InMemoryMembershipRepository` provides a zero-dependency
implementation for unit tests and local development.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram_example_platform.domain.membership import Membership


@runtime_checkable
class MembershipRepositoryProtocol(Protocol):
    """Persistence contract for :class:`Membership` entities.

    All methods are ``async`` because production implementations will issue
    I/O operations (SQL queries, etc.).
    """

    async def get(self, membership_id: str) -> Membership | None:
        """Fetch a membership by its unique identifier.

        Args:
            membership_id: UUID string of the membership to retrieve.

        Returns:
            The :class:`Membership` if found, otherwise ``None``.
        """
        ...

    async def find_by_tenant_and_user(
        self,
        tenant_id: str,
        user_id: str,
    ) -> Membership | None:
        """Fetch a membership by tenant and user identifiers.

        Args:
            tenant_id: The owning tenant's identifier.
            user_id: The user's identifier.

        Returns:
            The :class:`Membership` if found, otherwise ``None``.
        """
        ...

    async def save(self, membership: Membership) -> None:
        """Persist a membership entity (insert or update).

        Args:
            membership: The entity to persist.
        """
        ...

    async def list_by_tenant(self, tenant_id: str) -> list[Membership]:
        """Return all memberships for a given tenant.

        Args:
            tenant_id: The tenant whose memberships to return.

        Returns:
            List of :class:`Membership` entities for that tenant.
        """
        ...


class InMemoryMembershipRepository:
    """In-memory :class:`MembershipRepositoryProtocol` implementation.

    Stores memberships in a plain ``dict`` keyed by ``membership.id``.
    Suitable for unit tests and local development — not thread-safe.
    """

    def __init__(self) -> None:
        self._store: dict[str, Membership] = {}

    async def get(self, membership_id: str) -> Membership | None:
        """Fetch a membership by its unique identifier.

        Args:
            membership_id: UUID string of the membership to retrieve.

        Returns:
            The :class:`Membership` if found, otherwise ``None``.
        """
        return self._store.get(membership_id)

    async def find_by_tenant_and_user(
        self,
        tenant_id: str,
        user_id: str,
    ) -> Membership | None:
        """Fetch a membership by tenant and user identifiers.

        Args:
            tenant_id: The owning tenant's identifier.
            user_id: The user's identifier.

        Returns:
            The :class:`Membership` if found, otherwise ``None``.
        """
        for m in self._store.values():
            if m.tenant_id == tenant_id and m.user_id == user_id:
                return m
        return None

    async def save(self, membership: Membership) -> None:
        """Persist a membership entity (insert or update).

        Args:
            membership: The entity to persist.
        """
        self._store[membership.id] = membership

    async def list_by_tenant(self, tenant_id: str) -> list[Membership]:
        """Return all memberships for a given tenant.

        Args:
            tenant_id: The tenant whose memberships to return.

        Returns:
            List of :class:`Membership` entities for that tenant.
        """
        return [m for m in self._store.values() if m.tenant_id == tenant_id]


__all__ = [
    "InMemoryMembershipRepository",
    "MembershipRepositoryProtocol",
]
