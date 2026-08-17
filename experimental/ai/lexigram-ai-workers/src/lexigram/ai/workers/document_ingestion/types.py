"""
Document ingestion types and data models.

Contains all the core data structures used in document ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from lexigram.ai.workers.document_ingestion.parser import DocumentParser

ChunkingConfigDict = dict[str, Any]


class IngestionStatus(StrEnum):
    """Document ingestion status."""

    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """Simple document container for ingestion."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionProgress:
    """Track progress of document ingestion."""

    document_id: str
    status: IngestionStatus
    total_pages: int = 0
    pages_processed: int = 0
    total_chunks: int = 0
    chunks_processed: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    @property
    def progress_percent(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.chunks_processed / self.total_chunks) * 100

    def update(
        self,
        status: IngestionStatus | None = None,
        pages_processed: int | None = None,
        chunks_processed: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update progress tracking."""
        if status is not None:
            self.status = status
        if pages_processed is not None:
            self.pages_processed = pages_processed
        if chunks_processed is not None:
            self.chunks_processed = chunks_processed
        if error is not None:
            self.error = error
            self.status = IngestionStatus.FAILED
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "status": self.status.value,
            "total_pages": self.total_pages,
            "pages_processed": self.pages_processed,
            "total_chunks": self.total_chunks,
            "chunks_processed": self.chunks_processed,
            "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error,
        }


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    document_id: str
    success: bool
    chunks_created: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        document_id: str,
        chunks_created: int,
        duration: float,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Create successful ingestion result."""
        return cls(
            document_id=document_id,
            success=True,
            chunks_created=chunks_created,
            duration_seconds=duration,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls,
        document_id: str,
        error: str,
        duration: float,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Create failed ingestion result."""
        return cls(
            document_id=document_id,
            success=False,
            error=error,
            duration_seconds=duration,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "success": self.success,
            "chunks_created": self.chunks_created,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class DocumentIngestionJob:
    """JobProtocol configuration for document ingestion."""

    document_id: str
    file_path: Path
    collection_name: str
    parser: DocumentParser | None = None
    chunking_config: ChunkingConfigDict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    batch_size: int = 50  # Number of chunks to process in batch

    def to_job_kwargs(self) -> dict[str, Any]:
        """Convert to JobProtocol kwargs."""
        return {
            "document_id": self.document_id,
            "file_path": str(self.file_path),
            "collection_name": self.collection_name,
            "metadata": self.metadata,
            "batch_size": self.batch_size,
        }


# Forward references for type hints
if False:  # TYPE_CHECKING block for forward references
    pass
