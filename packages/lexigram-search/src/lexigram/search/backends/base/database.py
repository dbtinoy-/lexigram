"""Shared base class for database-backed search backends."""

from __future__ import annotations

from abc import abstractmethod
import re
from typing import TYPE_CHECKING, Any, cast

from lexigram.search.backends.filters import _FIELD_NAME_RE

if TYPE_CHECKING:
    from lexigram.contracts.core import HealthCheckResult
    from lexigram.contracts.data import DatabaseProviderProtocol


class DatabaseSearchBase:
    """Abstract base class for database-backed search backends.

    Provides shared functionality for:
    - Document extraction and preparation
    - SearchableProtocol text extraction
    - Index name sanitization
    - Common configuration handling

    Subclasses must implement:
    - _get_connection(): Return async database connection/pool
    - _execute_query(): Execute a query on the database
    - _ensure_table(): Create necessary tables/indexes
    """

    def __init__(self, **config: Any):
        self.config = config
        self.strict_validation = config.get("strict_validation", True)
        self._connection = None

    @abstractmethod
    async def connect(self) -> None:
        """Initialize the database connection."""

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""

    @abstractmethod
    async def _get_connection(self) -> Any:
        """Return an active connection (or pool) to the database."""

    def _prepare_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Prepare document for indexing with searchable text.

        Adds an `_searchable` field containing concatenated text from
        all text fields in the document for full-text search.
        """
        if "_searchable" in document:
            return document

        searchable = self._extract_searchable_text(document)
        prepared = document.copy()
        prepared["_searchable"] = searchable
        return prepared

    def _extract_searchable_text(self, document: dict) -> str:
        """Extract searchable text from document.

        Combines common text fields into a single searchable string.
        Override this in subclasses for custom field selection.
        """
        text_fields = ["title", "name", "description", "content", "text", "body"]
        parts = []

        # Priority fields first
        for field in text_fields:
            if document.get(field):
                parts.append(str(document[field]))

        # Then other string values under 200 chars
        for value in document.values():
            if isinstance(value, str) and len(value) < 200:
                if value not in parts:
                    parts.append(value)

        return " ".join(parts)

    def _sanitize_index_name(self, index: str) -> str:
        """Sanitize index name for safe use in SQL/queries.

        Replaces characters that could cause issues in table/collection names.
        Non-identifier characters are replaced with underscores so the result
        can never break out of a table-name context.
        """
        return re.sub(r"[^A-Za-z0-9_]", "_", index)

    def _extract_doc_id(self, document: dict[str, Any]) -> str:
        """Extract document ID from document.

        Checks for 'id' or '_id' fields.
        Raises ValueError if no ID found.
        """
        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            raise ValueError("Document must have an 'id' or '_id' field")
        return str(doc_id)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check database backend health.

        Tries to get a connection and execute a simple query.
        """
        from lexigram.contracts.core import HealthCheckResult, HealthStatus

        component = self.__class__.__name__
        try:
            conn = await self._get_connection()
            if conn is not None:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    details={"backend": component},
                )
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                error="No connection available",
            )
        except (OSError, ConnectionError, RuntimeError) as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"backend": component},
            )


class AsyncDatabaseSearchBase(DatabaseSearchBase):
    """Extended base class for async database backends.

    Provides additional utilities for async connection management
    and common async patterns used by SQL databases.

    The recommended pattern is to inject a ``DatabaseProviderProtocol``
    instance via the constructor so the search backend uses the shared
    connection pool managed by the framework rather than creating its own::

        backend = MySearchBackend(provider=db_provider)

    If ``provider`` is not supplied the subclass is responsible for
    implementing ``_get_pool()`` and managing its own pool lifecycle.
    Creating independent pools bypasses the framework's connection limits,
    observability, and lifecycle hooks.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol | None = None,
        **config: Any,
    ):
        super().__init__(**config)
        self._db_provider = provider
        self._pool = None
        self._config = config

    @property
    def pool(self) -> Any:
        """Get the connection pool (only applicable when no provider is used)."""
        return self._pool

    async def _get_connection(self) -> Any:
        """Return a connection via the injected provider, or fall back to pool.

        When a ``DatabaseProviderProtocol`` was supplied at construction time
        this method obtains a scoped connection from the provider — i.e. the
        full framework lifecycle (metrics, tracing, health) is preserved.

        When no provider is available the legacy pool path is used and
        ``_get_pool()`` is called; this path remains for backward compatibility
        but should not be used in new code.
        """
        if self._db_provider is not None:
            return await self._db_provider.get_scoped_connection()
        return await self._acquire_connection()

    async def _acquire_connection(self) -> Any:
        """Acquire a connection from the pool (legacy path — prefer provider)."""
        pool = await self._get_pool()
        if hasattr(pool, "acquire"):
            return await pool.acquire()
        return pool

    async def _get_pool(self) -> Any:
        """Get or create the database connection pool.

        Subclasses that do NOT inject a ``DatabaseProviderProtocol`` must
        override this method.  Prefer provider injection over pool creation.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must either receive a DatabaseProviderProtocol "
            "via its constructor or override _get_pool()."
        )

    async def _release_connection(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        pool = await self._get_pool()
        if hasattr(pool, "release"):
            await pool.release(conn)

    async def _execute_with_connection(
        self,
        query: str,
        params: list[Any] | None = None,
    ) -> list[Any]:
        """Execute a query with automatic connection management."""
        conn = await self._acquire_connection()
        try:
            if hasattr(conn, "fetch"):
                return cast(
                    "list[Any]",
                    await conn.fetch(query, *(params or [])),
                )
            if hasattr(conn, "execute"):
                result = await conn.execute(query, *(params or []))
                return cast("list[Any]", result)
            raise ValueError("Connection does not support query execution")
        finally:
            await self._release_connection(conn)

    async def _build_filter_clause(
        self,
        filters: dict[str, Any],
    ) -> tuple[str, list[Any]]:
        """Build SQL filter clause from filters dict.

        Returns (where_clause, params).
        """
        if not filters:
            return "", []

        from lexigram import serialization as json

        clauses: list[str] = []
        params: list[Any] = []

        for key, value in filters.items():
            if not _FIELD_NAME_RE.fullmatch(key):
                raise ValueError(f"Invalid filter field: {key!r}")
            if isinstance(value, dict):
                # Pass through operators directly - for JSONB/postgres
                clauses.append(f"document @> ${len(params) + 1}")
                params.append(json.dumps(value))
            elif isinstance(value, (list, tuple)):
                # IN clause
                placeholders = ", ".join(
                    f"${i + len(params) + 1}" for i in range(len(value))
                )
                clauses.append(f"document->>'{key}' IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"document->>'{key}' = ${len(params) + 1}")
                params.append(value)

        where_clause = " AND ".join(clauses)
        return where_clause, params


__all__ = ["AsyncDatabaseSearchBase", "DatabaseSearchBase"]
