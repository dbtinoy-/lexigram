"""SQLite schema management for FTS5 full-text search."""

from __future__ import annotations


class SQLiteSchemaManager:
    """Manages SQLite search schema creation and migrations."""

    def __init__(self, tokenizer: str = "porter unicode61"):
        self.tokenizer = tokenizer

    def get_create_table_sql(self, index_name: str) -> str:
        """Generate SQL to create the document storage table."""
        safe_index = self._sanitize(index_name)

        return f"""
            CREATE TABLE IF NOT EXISTS search_{safe_index} (
                id TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                searchable_text TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """

    def get_create_fts_table_sql(self, index_name: str) -> str:
        """Generate SQL to create the FTS5 virtual table."""
        safe_index = self._sanitize(index_name)

        return f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS search_{safe_index}_fts USING fts5(
                id,
                searchable_text,
                content=search_{safe_index},
                content_rowid=rowid,
                tokenize='{self.tokenizer}'
            )
        """

    def get_create_triggers_sql(self, index_name: str) -> list[str]:
        """Generate SQL to create triggers for FTS sync."""
        safe_index = self._sanitize(index_name)

        triggers = [
            # Insert trigger
            f"""
            CREATE TRIGGER IF NOT EXISTS search_{safe_index}_ai AFTER INSERT ON search_{safe_index} BEGIN
                INSERT INTO search_{safe_index}_fts(rowid, id, searchable_text)
                VALUES (new.rowid, new.id, json_extract(new.document, '$._searchable'));
            END
            """,
            # Delete trigger
            f"""
            CREATE TRIGGER IF NOT EXISTS search_{safe_index}_ad AFTER DELETE ON search_{safe_index} BEGIN
                INSERT INTO search_{safe_index}_fts(search_{safe_index}_fts, rowid, id, searchable_text)
                VALUES ('delete', old.rowid, old.id, json_extract(old.document, '$._searchable'));
            END
            """,
            # Update trigger
            f"""
            CREATE TRIGGER IF NOT EXISTS search_{safe_index}_au AFTER UPDATE ON search_{safe_index} BEGIN
                INSERT INTO search_{safe_index}_fts(search_{safe_index}_fts, rowid, id, searchable_text)
                VALUES ('delete', old.rowid, old.id, json_extract(old.document, '$._searchable'));
                INSERT INTO search_{safe_index}_fts(rowid, id, searchable_text)
                VALUES (new.rowid, new.id, json_extract(new.document, '$._searchable'));
            END
            """,
        ]

        return triggers

    def get_drop_table_sql(self, index_name: str) -> str:
        """Generate SQL to drop the search tables."""
        safe_index = self._sanitize(index_name)

        return f"""
            DROP TABLE IF EXISTS search_{safe_index};
            DROP TABLE IF EXISTS search_{safe_index}_fts;
        """

    def get_upsert_sql(self, index_name: str) -> str:
        """Generate SQL for upserting a document."""
        safe_index = self._sanitize(index_name)

        return f"""
            INSERT OR REPLACE INTO search_{safe_index} (id, document, searchable_text, updated_at)
            VALUES (?, ?, ?, datetime('now'))
        """

    def get_search_sql(self, index_name: str) -> str:
        """Generate SQL for basic text search using FTS5."""
        safe_index = self._sanitize(index_name)

        return f"""
            SELECT id, document, bm25(search_{safe_index}_fts) AS score
            FROM search_{safe_index}_fts
            WHERE search_{safe_index}_fts MATCH ?
            ORDER BY score
            LIMIT ? OFFSET ?
        """

    def get_search_highlight_sql(self, index_name: str) -> str:
        """Generate SQL for search with highlighting."""
        safe_index = self._sanitize(index_name)

        return f"""
            SELECT id, document, bm25(search_{safe_index}_fts) AS score,
                   highlight(search_{safe_index}_fts, 1, '<mark>', '</mark>') AS highlight
            FROM search_{safe_index}_fts
            WHERE search_{safe_index}_fts MATCH ?
            ORDER BY score
            LIMIT ? OFFSET ?
        """

    def get_search_snippet_sql(self, index_name: str) -> str:
        """Generate SQL for search with snippets."""
        safe_index = self._sanitize(index_name)

        return f"""
            SELECT id, document, bm25(search_{safe_index}_fts) AS score,
                   snippet(search_{safe_index}_fts, 1, '<mark>', '</mark>', '...', 30) AS snippet
            FROM search_{safe_index}_fts
            WHERE search_{safe_index}_fts MATCH ?
            ORDER BY score
            LIMIT ? OFFSET ?
        """

    def get_faceted_search_sql(
        self, index_name: str, facets: list[str]
    ) -> tuple[str, list[tuple[str, str]]]:
        """Generate SQL for faceted search."""
        safe_index = self._sanitize(index_name)

        search_sql = f"""
            SELECT id, document, bm25(search_{safe_index}_fts) AS score
            FROM search_{safe_index}_fts
            WHERE search_{safe_index}_fts MATCH ?
            ORDER BY score
            LIMIT ? OFFSET ?
        """

        facet_sqls = []
        for facet in facets:
            facet_sql = f"""
                SELECT document->>'{facet}' AS facet_value, COUNT(*) AS count
                FROM search_{safe_index}
                WHERE search_{safe_index}_fts MATCH ?
                GROUP BY document->>'{facet}'
                ORDER BY count DESC
            """
            facet_sqls.append((facet, facet_sql))

        return search_sql, facet_sqls

    def _sanitize(self, index_name: str) -> str:
        """Sanitize index name for safe SQL usage."""
        return index_name.replace("-", "_").replace(".", "_").replace(" ", "_")


__all__ = ["SQLiteSchemaManager"]
