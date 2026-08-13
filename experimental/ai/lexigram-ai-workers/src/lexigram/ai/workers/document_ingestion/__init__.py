"""
Document ingestion package.

Provides comprehensive document ingestion functionality for the Lexigram AI framework.
"""

from __future__ import annotations

from lexigram.ai.workers.document_ingestion.parser import (
    DocumentParser,
    UniversalDocumentParser,
)
from lexigram.ai.workers.document_ingestion.processor import DocumentProcessor
from lexigram.ai.workers.document_ingestion.progress import ProgressTracker
from lexigram.ai.workers.document_ingestion.types import (
    Document,
    DocumentIngestionJob,
    IngestionProgress,
    IngestionResult,
    IngestionStatus,
)
from lexigram.ai.workers.document_ingestion.worker import DocumentIngestionWorker

__all__ = [
    "Document",
    "DocumentIngestionJob",
    "DocumentIngestionWorker",
    "DocumentParser",
    "DocumentProcessor",
    "IngestionProgress",
    "IngestionResult",
    "IngestionStatus",
    "ProgressTracker",
    "UniversalDocumentParser",
]
