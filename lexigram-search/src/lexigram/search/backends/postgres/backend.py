"""PostgreSQL full-text search backend using ts_vector and GIN indexes.

Lives in ``lexigram-search`` (``lexigram.search.backends.postgres``).
The implementation depends only on ``DatabaseProviderProtocol`` from
``lexigram.contracts`` so it carries no dependency on ``lexigram-sql``
internals and belongs here alongside the other search backends.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.search.backends.filters import render_postgres
from lexigram.search.filterset import merge_filters, rule_to_filters
from lexigram.search.types import SearchResponse

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

# Facet keys are JSONB document keys, not SQL identifiers: they sit inside a
# single-quoted JSON path literal (document->>'...'), so they get a strict
# JSON-key guard instead of SQL identifier quoting.
_SAFE_JSON_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresDatabaseSearchBackend:
    """PostgreSQL FTS backend using ts_vector and GIN indexes.

    Implements the ``SearchEngine`` protocol structurally.  All database
    operations are delegated to the injected ``DatabaseProviderProtocol``
    so that connection pooling, instrumentation and lifecycle are managed
    by the framework rather than by this class.

    Args:
        provider: Database provider that supplies scoped connections.
        text_search_config: PostgreSQL text-search configuration name (language
            dictionary), e.g. ``"english"`` or ``"simple"``.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        text_search_config: str = "english",
    ) -> None:
        self._provider = provider
        self.text_search_config = text_search_config

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
        """Ensure the search table and GIN index exist for *index_name*."""
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
        """Create the backing table and GIN index for *index_name*."""
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
        """Full-text search using PostgreSQL ``websearch_to_tsquery``."""
        await self._ensure_table(index_name)

        sql = (
            f"SELECT id, document, "
            f"ts_rank(search_vector, websearch_to_tsquery($1, $2)) AS score "
            f"FROM search_{index_name} "
            f"WHERE search_vector @@ websearch_to_tsquery($1, $2)"
        )
        params: list[Any] = [self.text_search_config, query]

        if filters or rule:
            clause, filter_params = render_postgres(
                merge_filters(filters, rule_to_filters(rule)),
                offset=len(params) + 1,
            )
            sql += " AND " + clause
            params.extend(filter_params)

        sql += (
            " ORDER BY score DESC LIMIT $"
            + str(len(params) + 1)
            + " OFFSET $"
            + str(len(params) + 2)
        )
        params.extend([limit, offset])

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            result = await conn.execute(sql, params)
            rows = result.rows if hasattr(result, "rows") else []
            results = [
                {"id": row["id"], **row["document"], "_score": row["score"]}
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
                component="search.postgres",
                status=HealthStatus.HEALTHY,
            )
        except (OSError, ConnectionError, RuntimeError) as exc:
            return HealthCheckResult(
                component="search.postgres",
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
        """Upsert a single document into the PostgreSQL search table."""
        await self._ensure_table(index)
        doc_id = self._extract_doc_id(document)
        prepared = self._prepare_document(document)

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                f"""
                INSERT INTO search_{index} (id, document, search_vector)
                VALUES ($1, $2, to_tsvector($3, $2::text))
                ON CONFLICT (id) DO UPDATE SET
                    document = EXCLUDED.document,
                    search_vector = to_tsvector($3, EXCLUDED.document::text),
                    updated_at = NOW()
                """,
                [doc_id, json.dumps(prepared), self.text_search_config],
            )

        return {"id": doc_id, "status": "indexed"}

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a single document by ID."""
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            result = await conn.execute(
                f"DELETE FROM search_{index} WHERE id = $1",
                [doc_id],
            )
        return hasattr(result, "row_count") and result.row_count > 0

    async def index_many(
        self,
        documents: list[tuple[str, dict[str, Any]]],
        index: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Index multiple documents using PostgreSQL bulk upsert.

        Args:
            documents: Sequence of ``(document_id, document)`` pairs.
            index: Table name suffix; required for this backend.
        """
        if not documents:
            return
        if not index:
            raise ValueError(
                "index name is required for PostgresSearchBackend.index_many"
            )
        await self._ensure_table(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            for doc_id, document in documents:
                prepared = self._prepare_document(document)
                await conn.execute(
                    f"""
                    INSERT INTO search_{index} (id, document, search_vector)
                    VALUES ($1, $2, to_tsvector($3, $2::text))
                    ON CONFLICT (id) DO UPDATE SET
                        document = EXCLUDED.document,
                        search_vector = to_tsvector($3, EXCLUDED.document::text),
                        updated_at = NOW()
                    """,
                    [doc_id, json.dumps(prepared), self.text_search_config],
                )

    async def index_exists(self, index: str, **kwargs: Any) -> bool:
        """Check whether the PostgreSQL search table for *index* exists.

        Args:
            index: Index name (used as table suffix ``search_<index>``).

        Returns:
            ``True`` if the table exists.
        """
        safe_index = self._sanitize_index_name(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            result = await conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = $1",
                [f"search_{safe_index}"],
            )
            rows = result.rows if hasattr(result, "rows") else []
            return bool(rows)

    async def faceted_search(
        self,
        index: str,
        query: str,
        facets: list[str],
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Full-text search with per-field facet aggregations.

        Args:
            index: Index (table) to search.
            query: Search query string.
            facets: Document fields to compute facet counts for.
            filters: Optional JSON-containment filter.
            limit: Maximum number of result documents.
            offset: Result pagination offset.

        Returns:
            Mapping with keys ``hits``, ``total``, ``facets``, ``limit``, ``offset``.
        """
        safe_index = self._sanitize_index_name(index)
        for facet_field in facets:
            if not _SAFE_JSON_KEY_RE.match(facet_field):
                raise ValueError(f"Invalid facet field: {facet_field!r}")
        search_sql = (
            f"SELECT id, document, "
            f"ts_rank(search_vector, websearch_to_tsquery($1, $2)) AS score "
            f"FROM search_{safe_index} "
            f"WHERE search_vector @@ websearch_to_tsquery($1, $2)"
        )
        params: list[Any] = [self.text_search_config, query]

        if filters:
            search_sql += " AND document @> $" + str(len(params) + 1)
            params.append(json.dumps(filters))

        search_sql += (
            " ORDER BY score DESC LIMIT $"
            + str(len(params) + 1)
            + " OFFSET $"
            + str(len(params) + 2)
        )
        params.extend([limit, offset])

        facet_queries: list[tuple[str, str]] = []
        for facet_field in facets:
            fsql = (
                f"SELECT document->>'{facet_field}' AS facet_value, COUNT(*) AS count "
                f"FROM search_{safe_index} "
                f"WHERE search_vector @@ websearch_to_tsquery($1, $2)"
            )
            if filters:
                fsql += " AND document @> $" + str(len(params) - 1)
            fsql += f" GROUP BY document->>'{facet_field}' ORDER BY count DESC"
            facet_queries.append((facet_field, fsql))

        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()

            result = await conn.execute(search_sql, params)
            rows = result.rows if hasattr(result, "rows") else []
            results = [
                {"id": row["id"], **row["document"], "_score": row["score"]}
                for row in rows
            ]

            facets_result: dict[str, Any] = {}
            for facet_field, fsql in facet_queries:
                facet_params = params[:2]
                if filters:
                    facet_params = [*facet_params, params[2]]
                facet_result = await conn.execute(fsql, facet_params)
                facet_rows = facet_result.rows if hasattr(facet_result, "rows") else []
                facets_result[facet_field] = [
                    {"value": row["facet_value"], "count": row["count"]}
                    for row in facet_rows
                    if row.get("facet_value")
                ]

        return {
            "hits": results,
            "total": len(results),
            "facets": facets_result,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_table(self, index: str) -> None:
        """Create the search table and GIN index if they do not exist."""
        safe_index = self._sanitize_index_name(index)
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS search_{safe_index} (
                    id TEXT PRIMARY KEY,
                    document JSONB NOT NULL,
                    search_vector tsvector,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_search_{safe_index}_fts
                ON search_{safe_index} USING GIN (search_vector)
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

    def _prepare_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Add ``_searchable`` field to *document* unless already present."""
        if "_searchable" in document:
            return document
        prepared = document.copy()
        prepared["_searchable"] = self._extract_searchable_text(document)
        return prepared


__all__ = ["PostgresDatabaseSearchBackend"]
