"""Document loaders for RAG.

Load documents from various sources (PDF, HTML, Markdown, JSON, CSV, etc.).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.loaders.base import AbstractDocumentLoader
from lexigram.ai.rag.loaders.structured import CSVLoader as CSVLoader
from lexigram.ai.rag.loaders.structured import JSONLoader as JSONLoader
from lexigram.ai.rag.types import RAGError

try:
    import aiofiles

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


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
                    "Install with: pip install lexigram-ai-rag"
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
                    "Install with: pip install lexigram-ai-rag"
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
                        "Install with: pip install lexigram-ai-rag"
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
