"""
Document preprocessing modules.

This package provides modular document preprocessing capabilities
including OCR, table extraction, and metadata enrichment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.rag.exceptions import PreprocessingError
from lexigram.ai.rag.preprocessing.base import AbstractPreprocessor
from lexigram.ai.rag.preprocessing.document import PreprocessedDocument
from lexigram.ai.rag.preprocessing.enricher import MetadataEnricher
from lexigram.ai.rag.preprocessing.ocr import OCRPreprocessor
from lexigram.ai.rag.preprocessing.pipeline import PreprocessingPipeline
from lexigram.ai.rag.preprocessing.tables import TableExtractor
from lexigram.ai.rag.preprocessing.types import (
    DocumentMetadata,
    DocumentType,
    ExtractedImage,
    ExtractedTable,
    TableFormat,
)

__all__ = [
    "AbstractPreprocessor",
    "DocumentMetadata",
    "DocumentType",
    "ExtractedImage",
    "ExtractedTable",
    "MetadataEnricher",
    "OCRPreprocessor",
    "PreprocessedDocument",
    "PreprocessingError",
    "PreprocessingPipeline",
    "TableExtractor",
    "TableFormat",
]
