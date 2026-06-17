"""MySQL FULLTEXT search backend using MATCH AGAINST.

Lives in ``lexigram-search`` (``lexigram.search.backends.mysql``).
The implementation depends only on ``DatabaseProviderProtocol`` from
``lexigram.contracts`` so it carries no dependency on ``lexigram-sql``
internals and belongs here alongside the other search backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.search.backends.filters import render_mysql
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)


class MySQLDatabaseSearchBackend:
    """MySQL FULLTEXT search backend using MATCH AGAINST.

    Implements the ``SearchEngine`` protocol structurally.  All database
    operations are delegated to the injected ``DatabaseProviderProtocol``
    so that connection pooling, instrumentation and lifecycle are managed
    by the framework rather than by this class.

    Args:
        provider: Database provider that supplies scoped connections.
        fulltext_mode: MySQL FULLTEXT search mode — ``"NATURAL LANGUAGE"``
            (default) or ``"BOOLEAN"``.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        fulltext_mode: str = "NATURAL LANGUAGE",
    ) -> None:
        self._provider = provider
        self.fulltext_mode = fulltext_mode.upper()

    # ------------------------------------------------------------------
    # SearchEngine protocol methods
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish the database connection via the provider."""
        await self._provider.connect()

    async def close(self) -> None:
        """Release the database connection via the provider."""
        await self._provider.disconnect()

    async def ensure_schema(self, index_name: str) -> None:
        """Ensure the search table and FULLTEXT index exist for *index_name*."""
        await self._ensure_table(index_name)

    async def index(self, index_name: str, documents: list[dict[str, Any]]) -> bool:
        """Index multiple documents into *index_name*."""
        for doc in documents:
            await self.index_document(index_name, doc)
        return True

    async def update(
        self,
        index_name: str,
        document_id: str,
        document: dict[str, Any],
    ) -> bool:
        """Update a single document by ID."""
        document["id"] = document_id
        await self.index_document(index_name, document)
        return True

    async def delete(self, index_name: str, document_id: str) -> bool:
        """Delete a document from *index_name* by ID."""
        return await self.delete_document(index_name, document_id)

    async def create_index(
        self,
        index_name: str,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Create the backing table and FULLTEXT index for *index_name*."""
        await self._ensure_table(index_name)
        return True

    async def delete_index(self, index_name: str) -> bool:
        """Drop the backing table for *index_name*."""
        safe_index = self._sanitize_index_name(index_name)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(f"DROP TABLE IF EXISTS search_{safe_index}")
        return True

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
        rule: str | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """Full-text search using MySQL ``MATCH … AGAINST``."""
        await self._ensure_table(index_name)

        mode = self.fulltext_mode
        filter_clause = ""
        params: list[Any] = [query, query]
        if filters or rule:
            clause, filter_params = render_mysql(
                merge_filters(filters, rule_to_filters(rule))
            )
            filter_clause = " AND " + clause
            params.extend(filter_params)
        params.extend([limit, offset])

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            result = await conn.execute(
                f"""
                SELECT id, document,
                       MATCH(searchable_text) AGAINST(%s IN {mode} MODE) AS score
                FROM search_{index_name}
                WHERE MATCH(searchable_text) AGAINST(%s IN {mode} MODE)
                {filter_clause}
                ORDER BY score DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            rows = result.rows if hasattr(result, "rows") else []
            results = [
                {
                    "id": row["id"],
                    **json.loads(row["document"]),
                    "_score": float(row["score"]),
                }
                for row in rows
            ]

        return SearchResponse(
            results=results,
            total=len(results),
            page=offset // limit + 1 if limit else 1,
            per_page=limit,
            query=query,
            took_ms=0,
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Verify the backend is reachable."""
        try:
            async with self._provider.scoped_context():
                conn = await self._provider.get_scoped_connection()
                await conn.execute("SELECT 1")
            return HealthCheckResult(
                component="search.mysql",
                status=HealthStatus.HEALTHY,
            )
        except (OSError, ConnectionError, RuntimeError) as exc:
            return HealthCheckResult(
                component="search.mysql",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Higher-level convenience methods
    # ------------------------------------------------------------------

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Upsert a single document into the MySQL FULLTEXT search table."""
        await self._ensure_table(index)
        doc_id = self._extract_doc_id(document)
        searchable = self._extract_searchable_text(document)

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                f"""
                INSERT INTO search_{index} (id, document, searchable_text, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    document = VALUES(document),
                    searchable_text = VALUES(searchable_text),
                    updated_at = NOW()
                """,
                [doc_id, json.dumps(document), searchable],
            )

        return {"id": doc_id, "status": "indexed"}

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a single document by ID."""
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                f"DELETE FROM search_{index} WHERE id = %s",
                [doc_id],
            )
        return True

    async def index_many(
        self,
        documents: list[tuple[str, dict[str, Any]]],
        index: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Index multiple documents using MySQL bulk upsert.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index: Table name suffix; required for this backend.
        """
        if not documents:
            return
        if not index:
            raise ValueError("index name is required for MySQLSearchBackend.index_many")
        await self._ensure_table(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            for doc_id, document in documents:
                searchable = self._extract_searchable_text(document)
                await conn.execute(
                    f"""
                    INSERT INTO search_{index} (id, document, searchable_text)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        document = VALUES(document),
                        searchable_text = VALUES(searchable_text),
                        updated_at = NOW()
                    """,
                    [doc_id, json.dumps(document), searchable],
                )

    async def index_exists(self, index: str, **kwargs: Any) -> bool:
        """Check whether the MySQL search table for *index* exists.

        Args:
            index: Index name (used as table suffix ``search_<index>``).

        Returns:
            ``True`` if the table exists.
        """
        safe_index = self._sanitize_index_name(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            result = await conn.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = %s",
                [f"search_{safe_index}"],
            )
            rows = result.rows if hasattr(result, "rows") else []
            return bool(rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_table(self, index: str) -> None:
        """Create the search table and FULLTEXT index if they do not exist."""
        safe_index = self._sanitize_index_name(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS search_{safe_index} (
                    id VARCHAR(255) PRIMARY KEY,
                    document JSON NOT NULL,
                    searchable_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FULLTEXT INDEX ft_idx (searchable_text)
                ) ENGINE=InnoDB
                """
            )

    @staticmethod
    def _sanitize_index_name(name: str) -> str:
        """Return a safe SQL identifier by replacing special characters with underscores."""
        return name.replace("-", "_").replace(".", "_").replace(" ", "_")

    @staticmethod
    def _extract_doc_id(document: dict[str, Any]) -> str:
        """Extract the document ID from ``id`` or ``_id`` field.

        Raises:
            ValueError: If neither ``id`` nor ``_id`` is present.
        """
        doc_id = document.get("id") or document.get("_id")
        if not doc_id:
            raise ValueError("Document must have an 'id' or '_id' field")
        return str(doc_id)

    @staticmethod
    def _extract_searchable_text(document: dict[str, Any]) -> str:
        """Concatenate text from priority fields and any short string values."""
        priority_fields = ["title", "name", "description", "content", "text", "body"]
        parts: list[str] = []
        for field in priority_fields:
            if document.get(field):
                parts.append(str(document[field]))
        for value in document.values():
            if isinstance(value, str) and len(value) < 200 and value not in parts:
                parts.append(value)
        return " ".join(parts)


__all__ = ["MySQLDatabaseSearchBackend"]
