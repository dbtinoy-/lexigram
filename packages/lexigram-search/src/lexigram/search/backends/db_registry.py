"""DB search backend registry — unifies DB-backed search backend selection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend
from lexigram.search.backends.postgres import PostgresDatabaseSearchBackend
from lexigram.search.config import BackendType

DbSearchBackendBuilder = Callable[[Any], Any]


class DbSearchBackendRegistry:
    """Registry of DB-backed search backend builders, keyed by BackendType.

    A backend type maps to a builder that constructs the corresponding
    database-backed search backend from a database provider. Unknown (non-DB)
    backend types raise ``RuntimeError`` to match the historical provider
    behavior.

    Usage::

        registry = DbSearchBackendRegistry.with_defaults()
        backend = registry.create_db_backend(BackendType.POSTGRES, db_provider)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[BackendType, DbSearchBackendBuilder] = {}

    @classmethod
    def with_defaults(cls) -> DbSearchBackendRegistry:
        """Return a registry populated with the built-in DB backends.

        Returns:
            A :class:`DbSearchBackendRegistry` pre-registered for POSTGRES
            and MYSQL.
        """
        registry = cls()

        def _postgres(provider: Any) -> Any:
            return PostgresDatabaseSearchBackend(provider=provider)

        def _mysql(provider: Any) -> Any:
            return MySQLDatabaseSearchBackend(provider=provider)

        registry.register(BackendType.POSTGRES, _postgres)
        registry.register(BackendType.MYSQL, _mysql)
        return registry

    def register(
        self, backend_type: BackendType, builder: DbSearchBackendBuilder
    ) -> None:
        """Register a builder under a backend type.

        Args:
            backend_type: Backend type (e.g. ``BackendType.POSTGRES``).
            builder: Callable ``(provider) -> Any`` returning a search backend.
        """
        self._builders[backend_type] = builder

    def create_db_backend(self, backend_type: BackendType | None, provider: Any) -> Any:
        """Build a DB-backed search backend for a backend type.

        Args:
            backend_type: Backend type to dispatch on. ``None`` (or any
                non-DB type) is treated as unsupported.
            provider: Database provider passed to the backend constructor.

        Returns:
            An instantiated DB-backed search backend.

        Raises:
            RuntimeError: If *backend_type* is not a registered DB backend.
        """
        builder = self._builders.get(backend_type) if backend_type is not None else None
        if builder is None:
            raise RuntimeError(f"Unsupported DB-backed search backend: {backend_type}")
        return builder(provider)

    def backends(self) -> list[BackendType]:
        """Return the registered backend types.

        Returns:
            List of backend types in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, backend_type: BackendType) -> bool:
        return backend_type in self._builders


__all__ = ["DbSearchBackendBuilder", "DbSearchBackendRegistry"]
