"""Tests for admin storage upload types."""

import pytest

from lexigram.admin.services.storage.upload import StorageBackend, UploadedFile


class TestStorageBackend:
    """Tests for StorageBackend enum."""

    def test_storage_backend_values(self) -> None:
        """Test StorageBackend enum values."""
        assert StorageBackend.LOCAL.value == "local"
        assert StorageBackend.S3.value == "s3"
        assert StorageBackend.AZURE.value == "azure"
        assert StorageBackend.GCS.value == "gcs"
        assert StorageBackend.MEMORY.value == "memory"

    def test_storage_backend_members(self) -> None:
        """Test StorageBackend has expected members."""
        members = list(StorageBackend)
        assert len(members) == 5


class TestUploadedFile:
    """Tests for UploadedFile dataclass."""

    def test_uploaded_file_creation(self) -> None:
        """Test UploadedFile creation."""
        file = UploadedFile(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            storage_path="/uploads/test.pdf",
            url="https://example.com/uploads/test.pdf",
        )
        assert file.filename == "test.pdf"
        assert file.content_type == "application/pdf"
        assert file.size == 1024
        assert file.hash == ""

    def test_uploaded_file_with_hash(self) -> None:
        """Test UploadedFile with hash."""
        file = UploadedFile(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            storage_path="/uploads/test.pdf",
            url="https://example.com/uploads/test.pdf",
            hash="abc123",
        )
        assert file.hash == "abc123"
