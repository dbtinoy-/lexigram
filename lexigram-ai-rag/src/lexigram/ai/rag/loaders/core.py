"""Document loaders for RAG.

Load documents from various sources (PDF, HTML, Markdown, JSON, CSV, etc.).
"""

from __future__ import annotations

import asyncio
import csv
import io
from pathlib import Path
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.types import RAGError
from lexigram.serialization import dumps_str
from lexigram.serialization import loads as _loads

try:
    import aiofiles

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


class AbstractDocumentLoader:
    """Base class for document loaders."""

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load documents from source.

        Args:
            source: Document source (file path, URL, etc.)

        Returns:
            List of document chunks

        Raises:
            RAGError: If loading fails
        """
        raise NotImplementedError


class TextLoader(AbstractDocumentLoader):
    """Load plain text files.

    Example:
        >>> loader = TextLoader()
        >>> chunks = await loader.load("document.txt")
    """

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load text file.

        Args:
            source: Path to text file

        Returns:
            Single chunk with file content

        Raises:
            RAGError: If file cannot be read
        """
        try:
            path = Path(source)

            # Read file asynchronously
            if HAS_AIOFILES:
                async with aiofiles.open(path, encoding="utf-8") as f:
                    content = await f.read()
            else:
                content = await asyncio.to_thread(path.read_text, encoding="utf-8")

            return [
                Chunk(
                    text=content,
                    source=str(path),
                    chunk_index=0,
                    metadata={
                        "source": str(path),
                        "type": "text",
                    },
                ),
            ]

        except (OSError, UnicodeDecodeError) as e:
            msg = f"Failed to read text file {source}: {e}"
            raise RAGError(msg) from e
        except Exception as e:
            msg = f"Unexpected error loading text file {source}: {e}"
            raise RAGError(msg) from e


class PDFLoader(AbstractDocumentLoader):
    """Load PDF documents.

    Requires: pypdf or pdfplumber
    """

    def __init__(self, extract_images: bool = False):
        """Initialize PDF loader.

        Args:
            extract_images: Whether to extract images from PDFs
        """
        self.extract_images = extract_images

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load PDF file.

        Args:
            source: Path to PDF file

        Returns:
            List of chunks (one per page)

        Raises:
            RAGError: If PDF cannot be read
        """
        try:
            try:
                import pypdf  # type: ignore[import-not-found]
            except ImportError as e:
                msg = (
                    "PDF loading requires 'pypdf' package. "
                    "Install with: pip install lexigram-intelligence[rag]"
                )
                raise ImportError(msg) from e

            path = Path(source)
            exists = await asyncio.to_thread(path.exists)
            if not exists:
                raise FileNotFoundError(f"PDF file not found: {source}")

            # Load PDF asynchronously
            def _load_pdf() -> Any:
                chunks: list[Chunk] = []
                try:
                    with open(path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for page_num, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if text.strip():
                                chunks.append(
                                    Chunk(
                                        text=text,
                                        source=str(path),
                                        chunk_index=page_num,
                                        metadata={
                                            "source": str(path),
                                            "page": page_num + 1,
                                            "type": "pdf",
                                        },
                                    ),
                                )
                except Exception as e:
                    raise RAGError(f"PDF parsing error: {e}") from e
                return chunks

            return await asyncio.to_thread(_load_pdf)

        except (FileNotFoundError, ImportError, RAGError):
            raise
        except Exception as e:
            msg = f"Failed to load PDF {source}: {e}"
            raise RAGError(msg) from e


class MarkdownLoader(AbstractDocumentLoader):
    """Load Markdown documents.

    Preserves structure while extracting text.
    """

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load Markdown file.

        Args:
            source: Path to Markdown file

        Returns:
            Chunks split by headers

        Raises:
            RAGError: If file cannot be read
        """
        try:
            path = Path(source)

            # Read file asynchronously
            if HAS_AIOFILES:
                async with aiofiles.open(path, encoding="utf-8") as f:
                    content = await f.read()
            else:
                content = await asyncio.to_thread(path.read_text, encoding="utf-8")

            # Split by headers (simple approach)
            chunks: list[Chunk] = []
            current_chunk: list[str] = []
            current_header = None

            for line in content.split("\n"):
                if line.startswith("#"):
                    # Save previous chunk
                    if current_chunk:
                        chunks.append(
                            Chunk(
                                text="\n".join(current_chunk),
                                source=str(path),
                                chunk_index=len(chunks),
                                metadata={
                                    "source": str(path),
                                    "header": current_header,
                                    "type": "markdown",
                                },
                            ),
                        )
                    # Start new chunk
                    current_header = line.strip("# ")
                    current_chunk = [line]
                else:
                    current_chunk.append(line)

            # Save last chunk
            if current_chunk:
                chunks.append(
                    Chunk(
                        text="\n".join(current_chunk),
                        source=str(path),
                        chunk_index=len(chunks),
                        metadata={
                            "source": str(path),
                            "header": current_header,
                            "type": "markdown",
                        },
                    ),
                )
        except (OSError, UnicodeDecodeError) as e:
            msg = f"Failed to read Markdown {source}: {e}"
            raise RAGError(msg) from e
        except Exception as e:
            msg = f"Unexpected error loading Markdown {source}: {e}"
            raise RAGError(msg) from e
        else:
            return chunks


class HTMLLoader(AbstractDocumentLoader):
    """Load HTML documents.

    Requires: beautifulsoup4
    """

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load HTML file or URL.

        Args:
            source: Path or URL to HTML

        Returns:
            Single chunk with extracted text

        Raises:
            RAGError: If HTML cannot be parsed
        """
        try:
            try:
                from bs4 import BeautifulSoup  # type: ignore[import-not-found]
            except ImportError as e:
                msg = (
                    "HTML loading requires 'beautifulsoup4' package. "
                    "Install with: pip install lexigram-intelligence[rag]"
                )
                raise ImportError(msg) from e
            # Handle URL vs file path
            if str(source).startswith(("http://", "https://")):
                # Load from URL
                try:
                    import aiohttp
                except ImportError as _e:
                    msg = (
                        "HTML loading from URLs requires 'aiohttp' package. "
                        "Install with: pip install lexigram-intelligence[rag]"
                    )
                    raise ImportError(msg) from _e
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30.0),
                ) as _session:
                    async with _session.get(str(source)) as _resp:
                        html = await _resp.text()
            else:
                # Load from file
                path = Path(source)
                if HAS_AIOFILES:
                    async with aiofiles.open(path, encoding="utf-8") as f:
                        html = await f.read()
                else:
                    html = await asyncio.to_thread(path.read_text, encoding="utf-8")

            # Parse HTML
            def _parse_html() -> Any:
                soup = BeautifulSoup(html, "html.parser")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator="\n", strip=True)

            text = await asyncio.to_thread(_parse_html)

            return [
                Chunk(
                    text=text,
                    source=str(source),
                    chunk_index=0,
                    metadata={
                        "source": str(source),
                        "type": "html",
                    },
                ),
            ]

        except Exception as e:
            msg = f"Failed to load HTML {source}: {e}"
            raise RAGError(msg) from e


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
            if HAS_AIOFILES:
                async with aiofiles.open(path, encoding="utf-8") as f:
                    raw = await f.read()
            else:
                raw = await asyncio.to_thread(path.read_text, encoding="utf-8")

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
            if HAS_AIOFILES:
                async with aiofiles.open(path, encoding="utf-8", newline="") as f:
                    raw = await f.read()
            else:
                raw = await asyncio.to_thread(path.read_text, encoding="utf-8")

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
