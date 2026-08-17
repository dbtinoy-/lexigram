"""
Document parsing functionality.

Handles parsing of various document formats into unified Document objects.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any, Protocol, cast

from lexigram.ai.workers.document_ingestion.types import Document
from lexigram.contracts.ai.exceptions import RAGError


@dataclass(slots=True)
class _LoadedChunk:
    """Internal chunk representation produced by parser-side loaders."""

    text: str
    metadata: dict[str, Any]
    score: float | None = None


class DocumentLoader(Protocol):
    """Protocol for document loaders used by ``UniversalDocumentParser``."""

    async def load(self, source: str | Path) -> list[_LoadedChunk]:
        """Load a source into chunk-like records."""
        ...


class _TextLoader:
    async def load(self, source: str | Path) -> list[_LoadedChunk]:
        path = Path(source)
        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            msg = f"Failed to read text file {path}: {exc}"
            raise RAGError(msg) from exc

        return [
            _LoadedChunk(
                text=content,
                metadata={
                    "source": str(path),
                    "type": "text",
                },
            )
        ]


class _MarkdownLoader:
    async def load(self, source: str | Path) -> list[_LoadedChunk]:
        path = Path(source)
        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            msg = f"Failed to read markdown file {path}: {exc}"
            raise RAGError(msg) from exc

        chunks: list[_LoadedChunk] = []
        current_chunk: list[str] = []
        current_header: str | None = None

        for line in content.split("\n"):
            if line.startswith("#") and current_chunk:
                chunks.append(
                    _LoadedChunk(
                        text="\n".join(current_chunk),
                        metadata={
                            "source": str(path),
                            "header": current_header,
                            "type": "markdown",
                        },
                    )
                )
                current_chunk = [line]
                current_header = line.strip("# ")
                continue

            if line.startswith("#"):
                current_header = line.strip("# ")
            current_chunk.append(line)

        if current_chunk:
            chunks.append(
                _LoadedChunk(
                    text="\n".join(current_chunk),
                    metadata={
                        "source": str(path),
                        "header": current_header,
                        "type": "markdown",
                    },
                )
            )

        return chunks


class _HTMLLoader:
    async def load(self, source: str | Path) -> list[_LoadedChunk]:
        path = Path(source)
        try:
            html = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            msg = f"Failed to read HTML file {path}: {exc}"
            raise RAGError(msg) from exc

        without_scripts = re.sub(
            r"<script[\\s\\S]*?</script>",
            " ",
            html,
            flags=re.IGNORECASE,
        )
        without_styles = re.sub(
            r"<style[\\s\\S]*?</style>",
            " ",
            without_scripts,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", without_styles)
        text = re.sub(r"\\s+", " ", text).strip()

        return [
            _LoadedChunk(
                text=text,
                metadata={
                    "source": str(path),
                    "type": "html",
                },
            )
        ]


class _PDFLoader:
    async def load(self, source: str | Path) -> list[_LoadedChunk]:
        path = Path(source)

        def _read_pdf() -> list[_LoadedChunk]:
            import importlib

            try:
                pypdf_module = importlib.import_module("pypdf")
            except ImportError as exc:
                msg = "PDF loading requires the 'pypdf' package"
                raise RAGError(msg) from exc

            chunks: list[_LoadedChunk] = []
            with path.open("rb") as file_obj:
                reader = pypdf_module.PdfReader(file_obj)
                for page_index, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        chunks.append(
                            _LoadedChunk(
                                text=page_text,
                                metadata={
                                    "source": str(path),
                                    "type": "pdf",
                                    "page": page_index + 1,
                                },
                            )
                        )
            return chunks

        try:
            return cast("list[_LoadedChunk]", await asyncio.to_thread(_read_pdf))
        except (OSError, ValueError, TypeError, RAGError) as exc:
            msg = f"Failed to read PDF file {path}: {exc}"
            raise RAGError(msg) from exc


class DocumentParser(Protocol):
    """Protocol for document parsers."""

    async def parse(self, file_path: Path) -> Document:
        """Parse document from file."""
        ...

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from document."""
        ...


class UniversalDocumentParser:
    """Universal document parser using RAG loaders.

    Supports multiple document formats by delegating to appropriate loaders.
    """

    def __init__(self, allowed_root: Path | None = None) -> None:
        """Initialize parser with all supported loaders.

        Args:
            allowed_root: Optional directory that every parsed source must
                resolve inside of. When ``None`` (default), no containment
                check is performed and behavior is unchanged from earlier
                versions. When set, ``parse`` and ``extract_metadata`` raise
                ``RAGError`` for any source whose resolved path (symlinks
                followed) is not inside ``allowed_root``.
        """
        self.allowed_root = allowed_root.resolve() if allowed_root is not None else None
        self._loaders: dict[str, DocumentLoader] = {
            # Text formats
            ".txt": _TextLoader(),
            ".md": _MarkdownLoader(),
            ".markdown": _MarkdownLoader(),
            # Binary formats
            ".pdf": _PDFLoader(),
            # Web formats
            ".html": _HTMLLoader(),
            ".htm": _HTMLLoader(),
        }

    def _validate_source_within_root(self, file_path: Path) -> None:
        """Reject sources that resolve outside the configured allowed root.

        Args:
            file_path: Source path the caller wants to parse or inspect.

        Raises:
            RAGError: If ``allowed_root`` is set and the resolved path of
                ``file_path`` is not inside it.
        """
        if self.allowed_root is None:
            return
        resolved = file_path.resolve()
        if not resolved.is_relative_to(self.allowed_root):
            msg = (
                f"Access denied: {file_path} is outside the allowed root "
                f"{self.allowed_root}"
            )
            raise RAGError(msg)

    async def parse(self, file_path: Path) -> Document:
        """Parse document from file using appropriate loader.

        Args:
            file_path: Path to document file

        Returns:
            Parsed document

        Raises:
            RAGError: If ``allowed_root`` is set and the resolved
                ``file_path`` is outside it.
            ValueError: If file type is not supported
        """
        self._validate_source_within_root(file_path)

        if not file_path.exists():
            msg = f"Document not found: {file_path}"
            raise FileNotFoundError(msg)

        # Get file extension (lowercase)
        suffix = file_path.suffix.lower()

        # Get appropriate loader
        loader = self._loaders.get(suffix)
        if loader is None:
            supported = ", ".join(sorted(self._loaders.keys()))
            msg = f"Unsupported file type '{suffix}'. Supported types: {supported}"
            raise ValueError(msg)

        # Load document using the appropriate loader
        chunks = await loader.load(file_path)

        # Combine all chunks into a single document
        # Preserve chunk metadata in the document metadata
        combined_text = "\n\n".join(chunk.text for chunk in chunks)

        # Collect metadata from all chunks
        doc_metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": suffix,
            "total_chunks": len(chunks),
        }

        # Add chunk-specific metadata if available
        if chunks:
            # Use metadata from first chunk as base
            first_chunk = chunks[0]
            if first_chunk.metadata:
                doc_metadata.update(first_chunk.metadata)

            # Add page info if available (for PDFs)
            if "page" in first_chunk.metadata:
                doc_metadata["total_pages"] = max(
                    chunk.metadata.get("page", 0) for chunk in chunks if chunk.metadata
                )

        return Document(
            content=combined_text,
            metadata=doc_metadata,
        )

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from document without full parsing.

        Args:
            file_path: Path to document file

        Returns:
            Document metadata

        Raises:
            RAGError: If ``allowed_root`` is set and the resolved
                ``file_path`` is outside it.
        """
        self._validate_source_within_root(file_path)

        if not file_path.exists():
            msg = f"Document not found: {file_path}"
            raise FileNotFoundError(msg)

        # Basic file metadata
        stat = file_path.stat()
        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "file_modified": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            "file_type": file_path.suffix.lower(),
        }

        # Try to get additional metadata from loader if available
        suffix = file_path.suffix.lower()
        loader = self._loaders.get(suffix)

        if loader is not None:
            try:
                # For now, just load and extract from first chunk
                # In future, loaders could have dedicated metadata methods
                chunks = await loader.load(file_path)
                if chunks and chunks[0].metadata:
                    metadata.update(chunks[0].metadata)
            except (OSError, ValueError, TypeError, AttributeError):
                # If metadata extraction fails, just return basic metadata
                pass

        return metadata

    @property
    def supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        return sorted(self._loaders.keys())
