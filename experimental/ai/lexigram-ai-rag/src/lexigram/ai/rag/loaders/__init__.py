"""Document loaders for the Lexigram RAG pipeline."""

from __future__ import annotations

from lexigram.ai.rag.loaders.core import (
    AbstractDocumentLoader,
    CSVLoader,
    HTMLLoader,
    JSONLoader,
    MarkdownLoader,
    PDFLoader,
    TextLoader,
)
from lexigram.ai.rag.loaders.p1_loaders import (
    CodeLoader,
    DocxLoader,
    EmailLoader,
    ExcelLoader,
    SQLLoader,
    WebScraperLoader,
)
from lexigram.ai.rag.loaders.registry import (
    LoaderRegistry,
    SmartLoader,
    UnsupportedFormatError,
    build_default_registry,
)

__all__ = [
    "AbstractDocumentLoader",
    "CSVLoader",
    "CodeLoader",
    "DocxLoader",
    "EmailLoader",
    "ExcelLoader",
    "HTMLLoader",
    "JSONLoader",
    "LoaderRegistry",
    "MarkdownLoader",
    "PDFLoader",
    "SQLLoader",
    "SmartLoader",
    "TextLoader",
    "UnsupportedFormatError",
    "WebScraperLoader",
    "build_default_registry",
]
