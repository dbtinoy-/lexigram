"""Structured-data document loaders (JSON / JSONL and CSV / TSV)."""

from __future__ import annotations

import asyncio
import csv
import io
from pathlib import Path
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.loaders._io_utils import read_file_text
from lexigram.ai.rag.loaders.base import AbstractDocumentLoader
from lexigram.ai.rag.types import RAGError
from lexigram.serialization import dumps_str
from lexigram.serialization import loads as _loads


class JSONLoader(AbstractDocumentLoader):
    """Load JSON and JSONL documents.

    Produces one chunk per top-level array element (JSON) or per line
    (JSONL). Falls back to a single chunk for scalar/object JSON files.

    Example:
        >>> loader = JSONLoader()
        >>> chunks = await loader.load("records.json")
        >>> chunks = await loader.load("records.jsonl")
    """

    def __init__(self, *, text_key: str | None = None) -> None:
        """Initialize JSON loader.

        Args:
            text_key: When set, extract only this key's value as the chunk
                text. If not set, the raw JSON string of each record is used.
        """
        self.text_key = text_key

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load JSON or JSONL file.

        Args:
            source: Path to JSON or JSONL file.

        Returns:
            List of chunks — one per top-level item or one for the whole file.

        Raises:
            RAGError: If the file cannot be read or parsed.
        """
        try:
            path = Path(source)
            raw = await read_file_text(path)

            file_type = "jsonl" if path.suffix.lower() == ".jsonl" else "json"
            records: list[Any]

            if file_type == "jsonl":
                records = []
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        records.append(_loads(line))
            else:
                data = _loads(raw)
                records = data if isinstance(data, list) else [data]

            chunks: list[Chunk] = []
            for idx, record in enumerate(records):
                if self.text_key and isinstance(record, dict):
                    text = str(record.get(self.text_key, ""))
                    meta: dict[str, Any] = {
                        k: v for k, v in record.items() if k != self.text_key
                    }
                else:
                    text = record if isinstance(record, str) else dumps_str(record)
                    meta = {}

                chunks.append(
                    Chunk(
                        text=text,
                        source=str(path),
                        chunk_index=idx,
                        metadata={
                            "source": str(path),
                            "type": file_type,
                            "record_index": idx,
                            **meta,
                        },
                    )
                )

            return chunks

        except (OSError, UnicodeDecodeError) as e:
            msg = f"Failed to read JSON file {source}: {e}"
            raise RAGError(msg) from e
        except ValueError as e:
            msg = f"Failed to parse JSON file {source}: {e}"
            raise RAGError(msg) from e
        except Exception as e:
            msg = f"Unexpected error loading JSON file {source}: {e}"
            raise RAGError(msg) from e


class CSVLoader(AbstractDocumentLoader):
    """Load CSV and TSV documents.

    Produces one chunk per row by default, or batched rows when
    ``batch_size`` is greater than 1.

    Example:
        >>> loader = CSVLoader()
        >>> chunks = await loader.load("data.csv")
        >>> loader_tsv = CSVLoader(delimiter="\\t")
        >>> chunks = await loader_tsv.load("data.tsv")
    """

    def __init__(
        self,
        *,
        delimiter: str = ",",
        batch_size: int = 1,
        text_columns: list[str] | None = None,
    ) -> None:
        """Initialize CSV loader.

        Args:
            delimiter: Field delimiter (default: comma).
            batch_size: Number of rows per chunk. Defaults to 1.
            text_columns: If set, only these columns are included in chunk
                text. All columns are used when not set.
        """
        self.delimiter = delimiter
        self.batch_size = batch_size
        self.text_columns = text_columns

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load CSV or TSV file.

        Args:
            source: Path to CSV or TSV file.

        Returns:
            List of chunks — one per row or per batch of rows.

        Raises:
            RAGError: If the file cannot be read or parsed.
        """
        try:
            path = Path(source)
            raw = await read_file_text(path)

            def _parse_csv() -> list[dict[str, str]]:
                reader = csv.DictReader(
                    io.StringIO(raw),
                    delimiter=self.delimiter,
                )
                return list(reader)

            rows = await asyncio.to_thread(_parse_csv)

            chunks: list[Chunk] = []
            batch: list[dict[str, str]] = []

            def _row_to_text(row: dict[str, str]) -> str:
                if self.text_columns:
                    cols = {k: v for k, v in row.items() if k in self.text_columns}
                else:
                    cols = row
                return " ".join(f"{k}: {v}" for k, v in cols.items())

            for row_idx, row in enumerate(rows):
                batch.append(row)
                if len(batch) >= self.batch_size:
                    text = "\n".join(_row_to_text(r) for r in batch)
                    chunk_idx = row_idx // self.batch_size
                    chunks.append(
                        Chunk(
                            text=text,
                            source=str(path),
                            chunk_index=chunk_idx,
                            metadata={
                                "source": str(path),
                                "type": "csv",
                                "row_start": chunk_idx * self.batch_size,
                                "row_end": row_idx,
                            },
                        )
                    )
                    batch = []

            # Flush remaining rows
            if batch:
                chunk_idx = len(rows) // self.batch_size
                text = "\n".join(_row_to_text(r) for r in batch)
                chunks.append(
                    Chunk(
                        text=text,
                        source=str(path),
                        chunk_index=chunk_idx,
                        metadata={
                            "source": str(path),
                            "type": "csv",
                            "row_start": chunk_idx * self.batch_size,
                            "row_end": len(rows) - 1,
                        },
                    )
                )

            return chunks

        except (OSError, UnicodeDecodeError) as e:
            msg = f"Failed to read CSV file {source}: {e}"
            raise RAGError(msg) from e
        except csv.Error as e:
            msg = f"Failed to parse CSV file {source}: {e}"
            raise RAGError(msg) from e
        except Exception as e:
            msg = f"Unexpected error loading CSV file {source}: {e}"
            raise RAGError(msg) from e


__all__ = ["CSVLoader", "JSONLoader"]
