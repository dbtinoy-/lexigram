"""File Upload Service - Refactored to use lexigram-storage.

This service replaces the custom LocalStorageBackend with lexigram-storage
for S3/Azure/GCS
File upload service with validation and storage.

Provides a clean API for handling file uploads with validation,
storage backends, and security checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import BinaryIO
import uuid

from lexigram.contracts.infra.storage import BlobStoreProtocol, FileInfo, UploadOptions
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.storage.exceptions import StorageUnsupportedOperationError

logger = get_logger(__name__)


class StorageBackend(StrEnum):
    """Supported storage backends."""

    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"
    MEMORY = "memory"  # For testing


@dataclass
class UploadedFile:
    """Uploaded file metadata."""

    filename: str
    content_type: str
    size: int
    storage_path: str
    url: str
    hash: str = ""


@inject
class FileValidator:
    """File upload validator."""

    def __init__(
        self,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_extensions: set[str] | None = None,
        allowed_mimetypes: set[str] | None = None,
    ):
        """
        Initialize validator.

        Args:
            max_size: Maximum file size in bytes
            allowed_extensions: Set of allowed file extensions (e.g., {'.jpg', '.png'})
            allowed_mimetypes: Set of allowed MIME types
        """
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or set()
        self.allowed_mimetypes = allowed_mimetypes or set()

    def validate(self, filename: str, size: int, content_type: str) -> tuple[bool, str]:
        """
        Validate file.

        Returns:
            (is_valid, error_message)
        """
        # Check size
        if size > self.max_size:
            return False, f"File too large ({size} bytes, max {self.max_size})"

        # Check extension
        if self.allowed_extensions:
            ext = Path(filename).suffix.lower()
            if ext not in self.allowed_extensions:
                return False, f"File type not allowed: {ext}"

        # Check MIME type
        if self.allowed_mimetypes and content_type not in self.allowed_mimetypes:
            return False, f"MIME type not allowed: {content_type}"

        return True, ""


@inject
class FileUploadService:
    """DI-injectable file upload service using lexigram-storage.

    Benefits over custom LocalStorageBackend:
    - S3/Azure/GCS support out of the box
    - Presigned URLs for secure downloads
    - Production-tested storage patterns
    - Automatic retry logic
    - Cloud-native optimizations
    """

    def __init__(
        self,
        storage: BlobStoreProtocol,
        validator: FileValidator | None = None,
        upload_prefix: str = "admin",
    ):
        """
        Initialize file upload service.

        Args:
            storage: BlobStoreProtocol instance (injected)
            validator: File validator (defaults to permissive validator)
            upload_prefix: Prefix for uploaded files (e.g., "admin/uploads")
        """
        self.storage = storage
        self.validator = validator or FileValidator()
        self.upload_prefix = upload_prefix

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        public: bool = False,
    ) -> tuple[UploadedFile | None, str]:
        """
        Upload file using lexigram-storage.

        Args:
            file: File-like object
            filename: Original filename
            content_type: MIME type
            public: Whether file should be publicly accessible

        Returns:
            (UploadedFile, error_message) - UploadedFile is None if validation failed
        """
        # Read file content for validation and hashing
        content = file.read()
        size = len(content)

        # Validate
        is_valid, error = self.validator.validate(filename, size, content_type)
        if not is_valid:
            return None, error

        # Generate unique filename
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = f"{self.upload_prefix}/{unique_name}"

        # Calculate hash
        hasher = hashlib.sha256()
        hasher.update(content)
        file_hash = hasher.hexdigest()

        try:
            # Upload using lexigram-storage
            _file_info: FileInfo = await self.storage.upload(
                data=content,
                path=storage_path,
                options=UploadOptions(
                    content_type=content_type,
                    public=public,
                    metadata={"original_filename": filename, "sha256": file_hash},
                ),
            )

            # Get URL (presigned if private, public if public)
            if public:
                url = await self.storage.get_url(storage_path)
            else:
                from datetime import timedelta

                try:
                    url = await self.storage.get_presigned_url(
                        path=storage_path,
                        expires_in=timedelta(hours=1),
                    )
                except StorageUnsupportedOperationError:
                    from lexigram.logging import get_logger

                    logger = get_logger(__name__)
                    logger.warning(
                        "storage.presigned_fallback_to_public",
                        path=storage_path,
                        method="PUT",
                    )
                    url = await self.storage.get_url(storage_path)

            return (
                UploadedFile(
                    filename=filename,
                    content_type=content_type,
                    size=size,
                    storage_path=storage_path,
                    url=url,
                    hash=file_hash,
                ),
                "",
            )

        except (OSError, RuntimeError, AttributeError):
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            # Emit an explicit ERROR-level text message for caplog tests
            logger.exception("Upload failed for %s", filename)
            # Keep stacktrace for diagnostics
            logger.exception("Upload failed for %s", filename)
            return None, "Upload failed"
        except BaseException:
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Unexpected upload failure for %s", filename)
            logger.exception("Unexpected upload failure for %s", filename)
            return None, "Upload failed"

    async def delete(self, storage_path: str) -> bool:
        """
        Delete uploaded file.

        Args:
            storage_path: Path to file in storage

        Returns:
            True if deleted successfully
        """
        try:
            await self.storage.delete(storage_path)
            return True
        except (OSError, RuntimeError):
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Failed to delete storage path %s", storage_path)
            logger.exception("Failed to delete storage path %s", storage_path)
            return False
        except BaseException:
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Unexpected error deleting storage path %s", storage_path)
            logger.exception("Unexpected error deleting storage path %s", storage_path)
            return False

    async def get_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Get presigned URL for file.

        Args:
            storage_path: Path to file in storage
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        from datetime import timedelta

        try:
            return await self.storage.get_presigned_url(
                path=storage_path,
                expires_in=timedelta(seconds=expires_in),
            )
        except StorageUnsupportedOperationError:
            logger.warning(
                "storage.presigned_fallback_to_public",
                path=storage_path,
            )
            return await self.storage.get_url(storage_path)

    async def exists(self, storage_path: str) -> bool:
        """
        Check if file exists.

        Args:
            storage_path: Path to file in storage

        Returns:
            True if file exists
        """
        try:
            await self.storage.info(storage_path)
            return True
        except (OSError, RuntimeError):
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Failed to check existence for %s", storage_path)
            logger.exception("Failed to check existence for %s", storage_path)
            return False
        except BaseException:
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("Unexpected error checking existence for %s", storage_path)
            logger.exception("Unexpected error checking existence for %s", storage_path)
            return False
