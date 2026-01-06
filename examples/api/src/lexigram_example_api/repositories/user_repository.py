"""User repository — protocol contract and in-memory implementation.

The :class:`UserRepositoryProtocol` defines the persistence interface for
:class:`~lexigram_example_api.domain.User` entities.  Services depend on
the *protocol*, never the concrete implementation, honoring the Inversion of
Control principle.

:class:`InMemoryUserRepository` provides a zero-infrastructure implementation
suitable for integration tests and local development.  A production deployment
would swap it for a SQLAlchemy-backed repository registered via the DI
container.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.logging import get_logger

from lexigram_example_api.domain.user import User

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@runtime_checkable
class UserRepositoryProtocol(Protocol):
    """Persistence contract for :class:`~lexigram_example_api.domain.User`.

    All methods are async to accommodate SQL/Redis/HTTP-backed
    implementations without changing call-sites.
    """

    async def find_by_email(self, email: str) -> User | None:
        """Look up a user by their email address.

        Args:
            email: Email address to search (case-insensitive match expected
                from concrete implementations).

        Returns:
            The matching :class:`~lexigram_example_api.domain.User`, or
            ``None`` if no user exists for that email.
        """
        ...

    async def find_by_id(self, user_id: str) -> User | None:
        """Look up a user by their stable identifier.

        Args:
            user_id: UUID string of the user to retrieve.

        Returns:
            The matching :class:`~lexigram_example_api.domain.User`, or
            ``None`` if not found.
        """
        ...

    async def save(self, user: User) -> User:
        """Persist a user entity (insert or upsert).

        Args:
            user: The entity to persist.  The ``user_id`` field is used
                as the primary key.

        Returns:
            The persisted entity (may include server-set fields in SQL impls).
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryUserRepository:
    """Thread-safe, in-process user repository backed by two dicts.

    Intended for unit/integration testing and local ``docker compose up``
    development sessions.  Data is lost when the process exits.

    Note:
        This implementation is NOT safe for concurrent writes from multiple
        OS threads.  Async operations are synchronous under the hood because
        there is no I/O — no event-loop contention occurs.
    """

    def __init__(self) -> None:
        """Initialise empty in-memory stores."""
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, User] = {}

    async def find_by_email(self, email: str) -> User | None:
        """Look up a user by email.

        Args:
            email: Email to search (lowercased for normalisation).

        Returns:
            Matching user or ``None``.
        """
        return self._by_email.get(email.lower())

    async def find_by_id(self, user_id: str) -> User | None:
        """Look up a user by their stable identifier.

        Args:
            user_id: UUID string to search.

        Returns:
            Matching user or ``None``.
        """
        return self._by_id.get(user_id)

    async def save(self, user: User) -> User:
        """Upsert a user into both internal indices.

        Args:
            user: User entity to persist.

        Returns:
            The same entity (pass-through for interface consistency).
        """
        self._by_id[user.user_id] = user
        self._by_email[user.email.lower()] = user
        logger.debug("user_saved", user_id=user.user_id)
        return user
