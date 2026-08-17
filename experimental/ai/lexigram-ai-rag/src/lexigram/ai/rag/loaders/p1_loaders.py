"""P1 document loaders for RAG.

Compatibility facade for office, web, code, and SQL loaders."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.loaders._io_utils import read_file_text
from lexigram.ai.rag.loaders.office import DocxLoader, EmailLoader, ExcelLoader
from lexigram.ai.rag.loaders.web import WebScraperLoader
from lexigram.ai.rag.types import RAGError
from lexigram.contracts.data import DatabaseProviderProtocol

# ---------------------------------------------------------------------------
# CodeLoader
# ---------------------------------------------------------------------------

# Regex patterns that detect the start of a top-level definition per language
_CODE_SPLIT_PATTERNS: dict[str, str] = {
    ".py": r"^(?:async\s+)?(?:def|class)\s+\w+",
    ".js": r"^(?:function\s+\w+|class\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?(?:function|\(|[a-zA-Z_]))",
    ".ts": r"^(?:export\s+)?(?:async\s+)?(?:function\s+\w+|class\s+\w+|const\s+\w+\s*=)",
    ".java": r"^(?:public|private|protected|static|\s)+(?:class|interface|enum|\w+\s*\()",
    ".go": r"^func\s+",
    ".rs": r"^(?:pub\s+)?(?:fn|struct|enum|impl|trait|mod)\s+\w+",
    ".rb": r"^(?:def|class|module)\s+\w+",
}


class CodeLoader:
    """Load source code files with language-aware chunking.

    Splits at top-level function/class definitions using per-language
    regex patterns. Falls back to fixed-size chunking for unknown languages.

    No external dependencies required (optional: tree-sitter for precise AST
    parsing in future versions).
    """

    def __init__(self, *, max_chunk_lines: int = 100) -> None:
        """Initialize code loader.

        Args:
            max_chunk_lines: Maximum number of lines per chunk for fallback
                fixed-size splitting (unknown language extension).
        """
        self.max_chunk_lines = max_chunk_lines

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load a source code file.

        Args:
            source: Path to the source code file.

        Returns:
            List of chunks — one per top-level definition or fixed-size block.

        Raises:
            RAGError: If the file cannot be read.
        """
        try:
            path = Path(source)
            content = await read_file_text(path, encoding="utf-8")
            ext = path.suffix.lower()
            pattern = _CODE_SPLIT_PATTERNS.get(ext)

            chunks: list[Chunk] = []

            if pattern:
                split_re = re.compile(pattern, re.MULTILINE)
                lines = content.splitlines(keepends=True)
                split_indices = [0]
                for match in split_re.finditer(content):
                    # find line number of the match
                    line_no = content[: match.start()].count("\n")
                    if line_no > 0 and line_no not in split_indices:
                        split_indices.append(line_no)
                split_indices.append(len(lines))

                for i in range(len(split_indices) - 1):
                    block = "".join(lines[split_indices[i] : split_indices[i + 1]])
                    if block.strip():
                        chunks.append(
                            Chunk(
                                text=block,
                                source=str(path),
                                chunk_index=len(chunks),
                                metadata={
                                    "source": str(path),
                                    "type": "code",
                                    "language": ext.lstrip("."),
                                    "start_line": split_indices[i] + 1,
                                },
                            )
                        )
            else:
                # Fallback: fixed-size line batches
                lines = content.splitlines(keepends=True)
                for batch_start in range(0, len(lines), self.max_chunk_lines):
                    block = "".join(
                        lines[batch_start : batch_start + self.max_chunk_lines]
                    )
                    if block.strip():
                        chunks.append(
                            Chunk(
                                text=block,
                                source=str(path),
                                chunk_index=len(chunks),
                                metadata={
                                    "source": str(path),
                                    "type": "code",
                                    "language": ext.lstrip("."),
                                    "start_line": batch_start + 1,
                                },
                            )
                        )

            return chunks

        except (OSError, UnicodeDecodeError) as e:
            msg = f"Failed to read code file {source}: {e}"
            raise RAGError(msg) from e
        except Exception as e:
            msg = f"Unexpected error loading code file {source}: {e}"
            raise RAGError(msg) from e


# ---------------------------------------------------------------------------
# SQLLoader
# ---------------------------------------------------------------------------


class SQLLoader:
    """Load data from a SQL query result as document chunks.

    Uses ``DatabaseProviderProtocol`` for all database access — no direct
    driver imports. Each row becomes a chunk (or rows are batched).

    The caller is responsible for registering the provider and injecting it
    via constructor injection.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        *,
        query: str,
        params: dict[str, Any] | None = None,
        text_column: str | None = None,
        batch_size: int = 1,
        table_name: str = "query",
    ) -> None:
        """Initialize SQL loader.

        Args:
            db: Database provider (injected via DI container).
            query: SQL SELECT statement to execute.
            params: Optional query parameters.
            text_column: Column whose value is used as chunk text. When not
                set, all columns are joined into a key: value string.
            batch_size: Number of rows per chunk.
            table_name: Label used in metadata ``source`` field.
        """
        self._db = db
        self._query = query
        self._params = params or {}
        self._text_column = text_column
        self._batch_size = batch_size
        self._table_name = table_name

    async def load(self, source: str | Path = "") -> list[Chunk]:
        """Execute the SQL query and return a chunk per row (or batch).

        Args:
            source: Ignored — the data source is the DB connection passed at
                construction. Kept for interface compatibility.

        Returns:
            List of chunks, one per row or per batch of rows.

        Raises:
            RAGError: If the query fails.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows: list[dict[str, Any]] = await conn.fetch(
                    self._query, **self._params
                )

            label = f"sql://{self._table_name}"
            chunks: list[Chunk] = []
            batch: list[dict[str, Any]] = []

            def _row_text(row: dict[str, Any]) -> str:
                if self._text_column:
                    return str(row.get(self._text_column, ""))
                return " ".join(f"{k}: {v}" for k, v in row.items())

            for row_idx, row in enumerate(rows):
                batch.append(dict(row))
                if len(batch) >= self._batch_size:
                    text = "\n".join(_row_text(r) for r in batch)
                    chunk_idx = row_idx // self._batch_size
                    chunks.append(
                        Chunk(
                            text=text,
                            source=label,
                            chunk_index=chunk_idx,
                            metadata={
                                "source": label,
                                "type": "sql",
                                "table": self._table_name,
                                "row_start": chunk_idx * self._batch_size,
                                "row_end": row_idx,
                            },
                        )
                    )
                    batch = []

            if batch:
                chunk_idx = len(rows) // self._batch_size
                text = "\n".join(_row_text(r) for r in batch)
                chunks.append(
                    Chunk(
                        text=text,
                        source=label,
                        chunk_index=chunk_idx,
                        metadata={
                            "source": label,
                            "type": "sql",
                            "table": self._table_name,
                            "row_start": chunk_idx * self._batch_size,
                            "row_end": len(rows) - 1,
                        },
                    )
                )

            return chunks

        except RAGError:
            raise
        except Exception as e:
            msg = f"SQL query failed for '{self._table_name}': {e}"
            raise RAGError(msg) from e


__all__ = [
    "CodeLoader",
    "DocxLoader",
    "EmailLoader",
    "ExcelLoader",
    "SQLLoader",
    "WebScraperLoader",
]
