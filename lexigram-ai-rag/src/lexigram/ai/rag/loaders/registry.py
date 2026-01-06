"""Loader registry and smart loader for document format auto-detection.

Provides ``LoaderRegistry`` (extension/mime-to-loader map) and
``SmartLoader`` (auto-detects format and delegates to the right loader).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.loaders.core import AbstractDocumentLoader
from lexigram.ai.rag.types import RAGError
from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.registry import Registry

logger = get_logger(__name__)


class UnsupportedFormatError(RAGError):
    """Raised when no loader is registered for the given file format or URL."""

    _code: str = "LEX_ERR_RAG_016"

    def __init__(self, source: str) -> None:
        """Create an UnsupportedFormatError.

        Args:
            source: The source path or URL that could not be matched.
        """
        super().__init__(f"No loader registered for source: {source!r}")
        self.source = source


class LoaderRegistry:
    """Registry mapping file extensions and URL schemes to loader instances.

    Uses extension strings (including the leading dot) as keys, e.g.
    ``.pdf``, ``.json``. The special key ``"url"`` is used for HTTP/HTTPS
    sources.

    Follows the registry pattern — no ``if/elif`` chains.

    Example:
        >>> registry = LoaderRegistry()
        >>> registry.register([".txt", ".md"], TextLoader())
        >>> registry.register([".json", ".jsonl"], JSONLoader())
        >>> loader = registry.get_loader("report.json")
    """

    def __init__(self) -> None:
        """Initialize an empty LoaderRegistry."""
        self._registry: Registry[str, AbstractDocumentLoader] = Registry(name="loaders")

    def register(self, extensions: list[str], loader: AbstractDocumentLoader) -> None:
        """Register a loader for one or more extensions.

        Args:
            extensions: List of file extensions (e.g. ``[".pdf"]``) or
                the special value ``["url"]`` for HTTP/HTTPS sources.
            loader: Loader instance to handle those extensions.
        """
        for ext in extensions:
            self._registry.register(ext.lower(), loader)

    def get_loader(self, source: str) -> AbstractDocumentLoader | None:
        """Return the loader registered for this source, or None.

        Args:
            source: File path string or URL.

        Returns:
            The registered loader, or ``None`` if no match found.
        """
        src = str(source)
        parsed = urlparse(src)
        if parsed.scheme in ("http", "https"):
            return self._registry.get("url")
        ext = Path(src).suffix.lower()
        return self._registry.get(ext)

    async def load(self, source: str | Path, **kwargs: Any) -> list[Chunk]:
        """Resolve the loader and load the source.

        Args:
            source: File path or URL.
            **kwargs: Passed through to the resolved loader.

        Returns:
            List of chunks.

        Raises:
            UnsupportedFormatError: If no loader is registered for this
                extension or URL scheme.
            RAGError: If the underlying loader raises.
        """
        loader = self.get_loader(str(source))
        if loader is None:
            raise UnsupportedFormatError(str(source))
        return await loader.load(source, **kwargs)


def build_default_registry() -> LoaderRegistry:
    """Build a ``LoaderRegistry`` pre-populated with all built-in loaders.

    Only loaders whose optional dependencies are available are registered;
    a missing dependency causes that loader to be silently skipped.

    Returns:
        A ready-to-use registry with loaders registered for well-known
        extensions.
    """
    from lexigram.ai.rag.loaders.core import (
        CSVLoader,
        HTMLLoader,
        JSONLoader,
        MarkdownLoader,
        TextLoader,
    )
    from lexigram.ai.rag.loaders.p1_loaders import (
        CodeLoader,
        DocxLoader,
        EmailLoader,
        ExcelLoader,
        WebScraperLoader,
    )

    registry = LoaderRegistry()

    # P0 loaders (no optional deps)
    registry.register([".txt", ".rst"], TextLoader())
    registry.register([".md", ".markdown"], MarkdownLoader())
    registry.register([".json", ".jsonl"], JSONLoader())
    registry.register([".csv"], CSVLoader())
    registry.register([".tsv"], CSVLoader(delimiter="\t"))

    # P0 — beautifulsoup4 optional
    try:
        registry.register([".html", ".htm"], HTMLLoader())
        registry.register(["url"], WebScraperLoader())  # type: ignore[arg-type]
    except ImportError as e:
        logger.debug(
            "loader_registration_skipped",
            loaders=["HTMLLoader", "WebScraperLoader"],
            error=str(e),
        )

    # P0 — pypdf optional
    try:
        from lexigram.ai.rag.loaders.core import PDFLoader

        registry.register([".pdf"], PDFLoader())
    except ImportError as e:
        logger.debug("loader_registration_skipped", loaders=["PDFLoader"], error=str(e))

    # P1 loaders
    try:
        registry.register([".docx"], DocxLoader())  # type: ignore[arg-type]
    except ImportError as e:
        logger.debug(
            "loader_registration_skipped", loaders=["DocxLoader"], error=str(e)
        )

    try:
        registry.register([".xlsx", ".xls"], ExcelLoader())  # type: ignore[arg-type]
    except ImportError as e:
        logger.debug(
            "loader_registration_skipped", loaders=["ExcelLoader"], error=str(e)
        )

    registry.register([".eml"], EmailLoader())  # type: ignore[arg-type]

    code_loader = CodeLoader()
    registry.register(
        [".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".cpp", ".c", ".cs"],
        code_loader,  # type: ignore[arg-type]
    )

    return registry


class SmartLoader:
    """Auto-detect file format from extension or URL scheme and delegate.

    Uses :class:`LoaderRegistry` internally. If no custom registry is
    provided, :func:`build_default_registry` is called on first use.

    Example:
        >>> loader = SmartLoader()
        >>> chunks = await loader.load("report.pdf")
        >>> chunks = await loader.load("https://example.com/page")
    """

    def __init__(self, registry: LoaderRegistry | None = None) -> None:
        """Initialize SmartLoader.

        Args:
            registry: Optional pre-configured registry. Defaults to the
                result of :func:`build_default_registry`.
        """
        self._registry = registry

    @property
    def registry(self) -> LoaderRegistry:
        """Lazy-initialize the registry on first access."""
        if self._registry is None:
            self._registry = build_default_registry()
        return self._registry

    async def load(self, source: str | Path, **kwargs: Any) -> list[Chunk]:
        """Load a source using the auto-detected loader.

        Args:
            source: File path or URL.
            **kwargs: Passed through to the resolved loader.

        Returns:
            List of chunks.

        Raises:
            UnsupportedFormatError: If the file extension or URL scheme has
                no registered loader.
            RAGError: If loading fails.
        """
        return await self.registry.load(source, **kwargs)
