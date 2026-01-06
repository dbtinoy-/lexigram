"""Tests for document ingestion types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.ai.workers.document_ingestion.types import (
    Document,
    DocumentIngestionJob,
    IngestionProgress,
    IngestionResult,
    IngestionStatus,
)


class TestIngestionStatus:
    """Test IngestionStatus enum."""

    def test_values(self) -> None:
        """Test all ingestion status values."""
        assert IngestionStatus.PENDING.value == "pending"
        assert IngestionStatus.PARSING.value == "parsing"
        assert IngestionStatus.CHUNKING.value == "chunking"
        assert IngestionStatus.EMBEDDING.value == "embedding"
        assert IngestionStatus.STORING.value == "storing"
        assert IngestionStatus.COMPLETED.value == "completed"
        assert IngestionStatus.FAILED.value == "failed"

    def test_is_str_enum(self) -> None:
        """Test it's a StrEnum."""
        assert isinstance(IngestionStatus.PENDING, str)


class TestDocument:
    """Test Document dataclass."""

    def test_creation_basic(self) -> None:
        """Test creating a Document with basic fields."""
        doc = Document(content="Hello world")
        assert doc.content == "Hello world"
        assert doc.metadata == {}

    def test_creation_with_metadata(self) -> None:
        """Test creating a Document with metadata."""
        doc = Document(content="Test", metadata={"author": "test", "size": 100})
        assert doc.content == "Test"
        assert doc.metadata["author"] == "test"
        assert doc.metadata["size"] == 100

    def test_default_metadata_is_empty_dict(self) -> None:
        """Test default metadata is an empty dict."""
        doc1 = Document(content="test1")
        doc2 = Document(content="test2")
        doc1.metadata["key"] = "value"
        assert "key" not in doc2.metadata


class TestIngestionProgress:
    """Test IngestionProgress dataclass."""

    def test_creation(self) -> None:
        """Test creating IngestionProgress."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PENDING,
        )
        assert progress.document_id == "doc-1"
        assert progress.status == IngestionStatus.PENDING

    def test_default_values(self) -> None:
        """Test default values for IngestionProgress."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PENDING,
        )
        assert progress.total_pages == 0
        assert progress.pages_processed == 0
        assert progress.total_chunks == 0
        assert progress.chunks_processed == 0
        assert progress.error is None
        assert progress.started_at is not None
        assert progress.updated_at is not None

    def test_progress_percent_zero_chunks(self) -> None:
        """Test progress_percent returns 0 when total_chunks is 0."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PENDING,
            total_chunks=0,
        )
        assert progress.progress_percent == 0.0

    def test_progress_percent_partial(self) -> None:
        """Test progress_percent calculates correctly."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.CHUNKING,
            total_chunks=100,
            chunks_processed=50,
        )
        assert progress.progress_percent == 50.0

    def test_progress_percent_complete(self) -> None:
        """Test progress_percent returns 100 when complete."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.COMPLETED,
            total_chunks=100,
            chunks_processed=100,
        )
        assert progress.progress_percent == 100.0

    def test_update_status(self) -> None:
        """Test update sets status."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PENDING,
        )
        progress.update(status=IngestionStatus.PARSING)
        assert progress.status == IngestionStatus.PARSING

    def test_update_pages_processed(self) -> None:
        """Test update sets pages_processed."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PARSING,
        )
        progress.update(pages_processed=10)
        assert progress.pages_processed == 10

    def test_update_chunks_processed(self) -> None:
        """Test update sets chunks_processed."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.CHUNKING,
        )
        progress.update(chunks_processed=50)
        assert progress.chunks_processed == 50

    def test_update_error_sets_failed_status(self) -> None:
        """Test update with error sets status to FAILED."""
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PARSING,
        )
        progress.update(error="Something went wrong")
        assert progress.error == "Something went wrong"
        assert progress.status == IngestionStatus.FAILED

    def test_update_updates_timestamp(self) -> None:
        """Test update updates the updated_at timestamp."""
        before = datetime.now(UTC)
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.PENDING,
        )
        progress.update(status=IngestionStatus.PARSING)
        after = datetime.now(UTC)
        assert before <= progress.updated_at <= after

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        now = datetime.now(UTC)
        progress = IngestionProgress(
            document_id="doc-1",
            status=IngestionStatus.COMPLETED,
            total_chunks=100,
            chunks_processed=100,
            started_at=now,
            updated_at=now,
        )
        d = progress.to_dict()
        assert d["document_id"] == "doc-1"
        assert d["status"] == "completed"
        assert d["total_chunks"] == 100
        assert d["chunks_processed"] == 100
        assert d["progress_percent"] == 100.0


class TestIngestionResult:
    """Test IngestionResult dataclass."""

    def test_creation(self) -> None:
        """Test creating IngestionResult."""
        result = IngestionResult(
            document_id="doc-1",
            success=True,
            chunks_created=10,
            duration_seconds=5.5,
        )
        assert result.document_id == "doc-1"
        assert result.success is True
        assert result.chunks_created == 10
        assert result.duration_seconds == 5.5

    def test_success_result_factory(self) -> None:
        """Test success_result factory method."""
        result = IngestionResult.success_result(
            document_id="doc-1",
            chunks_created=10,
            duration=5.5,
        )
        assert result.success is True
        assert result.chunks_created == 10
        assert result.duration_seconds == 5.5
        assert result.error is None

    def test_success_result_with_metadata(self) -> None:
        """Test success_result with custom metadata."""
        result = IngestionResult.success_result(
            document_id="doc-1",
            chunks_created=10,
            duration=5.5,
            metadata={"key": "value"},
        )
        assert result.metadata == {"key": "value"}

    def test_failure_result_factory(self) -> None:
        """Test failure_result factory method."""
        result = IngestionResult.failure_result(
            document_id="doc-1",
            error="Parse error",
            duration=2.0,
        )
        assert result.success is False
        assert result.error == "Parse error"
        assert result.duration_seconds == 2.0

    def test_failure_result_with_metadata(self) -> None:
        """Test failure_result with custom metadata."""
        result = IngestionResult.failure_result(
            document_id="doc-1",
            error="Parse error",
            duration=2.0,
            metadata={"retry": True},
        )
        assert result.metadata == {"retry": True}

    def test_to_dict_success(self) -> None:
        """Test to_dict for successful result."""
        result = IngestionResult(
            document_id="doc-1",
            success=True,
            chunks_created=10,
            duration_seconds=5.5,
        )
        d = result.to_dict()
        assert d["document_id"] == "doc-1"
        assert d["success"] is True
        assert d["chunks_created"] == 10

    def test_to_dict_failure(self) -> None:
        """Test to_dict for failed result."""
        result = IngestionResult(
            document_id="doc-1",
            success=False,
            error="Parse error",
            duration_seconds=2.0,
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Parse error"


class TestDocumentIngestionJob:
    """Test DocumentIngestionJob dataclass."""

    def test_creation(self) -> None:
        """Test creating DocumentIngestionJob."""
        from pathlib import Path

        job = DocumentIngestionJob(
            document_id="doc-1",
            file_path=Path("/tmp/test.pdf"),
            collection_name="docs",
        )
        assert job.document_id == "doc-1"
        assert job.file_path == Path("/tmp/test.pdf")
        assert job.collection_name == "docs"

    def test_default_batch_size(self) -> None:
        """Test default batch_size is 50."""
        from pathlib import Path

        job = DocumentIngestionJob(
            document_id="doc-1",
            file_path=Path("/tmp/test.pdf"),
            collection_name="docs",
        )
        assert job.batch_size == 50

    def test_custom_batch_size(self) -> None:
        """Test custom batch_size."""
        from pathlib import Path

        job = DocumentIngestionJob(
            document_id="doc-1",
            file_path=Path("/tmp/test.pdf"),
            collection_name="docs",
            batch_size=100,
        )
        assert job.batch_size == 100

    def test_to_job_kwargs(self) -> None:
        """Test to_job_kwargs serialization."""
        from pathlib import Path

        job = DocumentIngestionJob(
            document_id="doc-1",
            file_path=Path("/tmp/test.pdf"),
            collection_name="docs",
            metadata={"author": "test"},
            batch_size=75,
        )
        kwargs = job.to_job_kwargs()
        assert kwargs["document_id"] == "doc-1"
        assert kwargs["file_path"] == "/tmp/test.pdf"
        assert kwargs["collection_name"] == "docs"
        assert kwargs["metadata"] == {"author": "test"}
        assert kwargs["batch_size"] == 75