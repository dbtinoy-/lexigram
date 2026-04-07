"""SQLite FTS5 search backend."""

from __future__ import annotations

from typing import Any

from lexigram import serialization as json
from lexigram.result import Err, Ok, Result
from lexigram.search.backends.base import SearchBackendBase
from lexigram.search.backends.base.database import AsyncDatabaseSearchBase
from lexigram.search.config import SQLiteSearchConfig
from lexigram.search.exceptions import SearchError
from lexigram.search.types import SearchResponse, SearchResult


class SQLiteSearchBackend(AsyncDatabaseSearchBase, SearchBackendBase):
    """SQLite FTS5 full-text search backend."""

    def __init__(self, config: SQLiteSearchConfig | dict[str, Any] | None = None):
        if isinstance(config, dict):
            config = SQLiteSearchConfig(**config)
        elif config is None:
            config = SQLiteSearchConfig()

        super().__init__(**config.model_dump())
        self.sqlite_config = config
        self._conn: Any = None

    async def _get_connection(self) -> Any:
        """Get or create the database connection."""
        import aiosqlite

        if self._conn is None:
            self._conn = await aiosqlite.connect(self.sqlite_config.db_path)
        return self._conn

    async def _get_client(self) -> Any:
        """Get or create the backend client."""
        return await self._get_connection()

    async def connect(self) -> None:
        """Initialize the database connection."""
        await self._get_connection()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
        self._conn: Any = None  # type: ignore[no-redef]

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Index a document into SQLite FTS5."""
        await self._ensure_tables(index)

        # Use base class helper
        doc_id = self._extract_doc_id(document)
        searchable = self._extract_searchable_text(document)

        conn = await self._get_connection()
        await conn.execute(
            f"""
            INSERT OR REPLACE INTO search_{index} (id, document, searchable_text, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (doc_id, json.dumps(document), searchable),
        )
        await conn.commit()

        return {"id": doc_id, "status": "indexed"}

    async def search(  # type: ignore[override]
        self,
        index: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> Result[SearchResponse, SearchError]:
        """Search documents using SQLite FTS5."""
        try:
            await self._ensure_tables(index)

            conn = await self._get_connection()

            safe_index = self._sanitize_index_name(index)

            sql = f"""
                SELECT id, document, bm25(search_{safe_index}_fts) AS score
                FROM search_{safe_index}_fts
                WHERE search_{safe_index}_fts MATCH ?
            """
            params = [query]

            sql += f" ORDER BY score LIMIT {limit} OFFSET {offset}"

            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()

            results = [
                SearchResult(
                    id=row[0],
                    score=abs(row[2]),
                    data=json.loads(row[1]),
                )
                for row in rows
            ]

            return Ok(
                SearchResponse(
                    results=results,
                    total=len(results),
                    page=offset // limit + 1 if limit else 1,
                    per_page=limit,
                    query=query,
                )
            )
        except Exception as exc:  # noqa: BLE001
            return Err(SearchError(f"SQLite search failed: {exc}"))

    async def delete_document(self, index: str, doc_id: str, **kwargs: Any) -> bool:
        """Delete a document from the index."""
        await self._ensure_tables(index)

        conn = await self._get_connection()

        await conn.execute(
            f"DELETE FROM search_{index} WHERE id = ?",
            (doc_id,),
        )
        await conn.commit()

        return True

    def _extract_searchable_text(self, document: dict) -> str:
        """Extract searchable text from document."""
        text_fields = ["title", "name", "description", "content", "text", "body"]
        parts = []

        for field in text_fields:
            if document.get(field):
                parts.append(str(document[field]))

        for value in document.values():
            if isinstance(value, str) and len(value) < 200:
                parts.append(value)

        return " ".join(parts)

    async def _ensure_tables(self, index: str) -> None:
        """Ensure the search tables exist."""
        # Use base class helper for sanitization
        safe_index = self._sanitize_index_name(index)

        conn = await self._get_connection()

        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS search_{safe_index} (
                id TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                searchable_text TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        await conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS search_{safe_index}_fts USING fts5(
                id,
                searchable_text,
                content=search_{safe_index},
                content_rowid=rowid,
                tokenize='{self.sqlite_config.tokenizer}'
            )
        """)

        await conn.commit()

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
        """Search with faceted aggregations.

        Args:
            index: The index to search
            query: The search query
            facets: List of fields to facet on
            filters: Optional filters
            limit: Number of results
            offset: Offset for pagination

        Returns:
            Dict with hits, total, and facets
        """
        safe_index = self._sanitize_index_name(index)
        conn = await self._get_connection()

        # Main search query
        sql = f"""
            SELECT id, document, bm25(search_{safe_index}_fts) AS score
            FROM search_{safe_index}_fts
            WHERE search_{safe_index}_fts MATCH ?
        """
        params = [query]

        sql += f" ORDER BY score LIMIT {limit} OFFSET {offset}"

        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()

        results = [
            {"id": row[0], **json.loads(row[1]), "_score": abs(row[2])} for row in rows
        ]

        # Facet queries
        facets_result = {}
        for facet_field in facets:
            facet_sql = f"""
                SELECT document->'{facet_field}' AS facet_value, COUNT(*) AS count
                FROM search_{safe_index}
                WHERE search_{safe_index}_fts MATCH ?
                GROUP BY document->'{facet_field}'
                ORDER BY count DESC
            """
            facet_cursor = await conn.execute(facet_sql, [query])
            facet_rows = await facet_cursor.fetchall()

            facets_result[facet_field] = [
                {"value": row[0], "count": row[1]} for row in facet_rows if row[0]
            ]

        return {
            "hits": results,
            "total": len(results),
            "facets": facets_result,
            "limit": limit,
            "offset": offset,
        }


__all__ = ["SQLiteSearchBackend"]
