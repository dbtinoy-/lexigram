"""
Main storage service implementation.

Provides the AdminStorageService class for file upload management.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
import hashlib
from typing import Any, BinaryIO

from lexigram.admin.config import AdminStorageConfig
from lexigram.admin.exceptions import DataError
from lexigram.admin.services.storage.types import (
    AdminFileInfo,
    AdminUploadOptions,
)
from lexigram.admin.services.storage.utils import get_content_type
from lexigram.contracts.infra.storage import BlobStoreProtocol, FileInfo
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.storage.exceptions import StorageUnsupportedOperationError

logger = get_logger(__name__)


@inject
class AdminStorageService:
    """Storage service for admin file management.

    Provides a unified interface for file uploads with:
    - Validation (size, type)
    - Path generation
    - Presigned URLs
    - Resource association

    Example:
        >>> storage = AdminStorageService(blob_store, config)
        >>>
        >>> # Upload a file
        >>> result = await storage.upload(
        ...     data=file_bytes,
        ...     filename="avatar.jpg",
        ...     options=AdminUploadOptions(
        ...         resource_type="users",
        ...         resource_id=123,
        ...     ),
        ... )
        >>>
        >>> # Get presigned URL
        >>> url = await storage.get_download_url(result.file_info.path)
    """

    def __init__(
        self,
        blob_store: BlobStoreProtocol,
        config: AdminStorageConfig | None = None,
    ):
        self.config = config or AdminStorageConfig()
        self._store: BlobStoreProtocol = blob_store

    def validate_upload(
        self,
        data: bytes | BinaryIO,
        filename: str,
        options: AdminUploadOptions | None = None,
    ) -> tuple[bool, str | None]:
        """Validate file before upload.

        Args:
            data: File content
            filename: Original filename
            options: Upload options

        Returns:
            (is_valid, error_message)
        """
        # Get content type
        content_type = options.content_type if options else None
        if not content_type:
            content_type = get_content_type(filename)

        # Check content type
        allowed_types = (
            options.allowed_types
            if options and options.allowed_types
            else self.config.allowed_content_types
        )
        if allowed_types and content_type not in allowed_types:
            return False, f"Content type not allowed: {content_type}"

        # Check size
        max_size = (
            options.max_size
            if options and options.max_size
            else self.config.max_file_size
        )
        if isinstance(data, bytes):
            size = len(data)
        elif hasattr(data, "seek") and hasattr(data, "tell"):
            pos = data.tell()
            data.seek(0, 2)
            size = data.tell()
            data.seek(pos)
        else:
            size = 0  # Can't determine

        if max_size and size > max_size:
            return False, f"File too large: {size} bytes (max: {max_size})"

        return True, None

    async def upload(
        self,
        data: bytes | BinaryIO | AsyncIterator[bytes],
        filename: str,
        options: AdminUploadOptions | None = None,
        uploaded_by: Any = None,
    ) -> Result[AdminFileInfo, DataError]:
        """Upload a file.

        Args:
            data: File content
            filename: Original filename
            options: Upload options
            uploaded_by: User who uploaded the file

        Returns:
            Result containing AdminFileInfo on success, DataError on failure.
        """
        # Validate (only for bytes/BinaryIO)
        if isinstance(data, (bytes, BinaryIO)) or hasattr(data, "read"):
            is_valid, error = self.validate_upload(data, filename, options)  # type: ignore[arg-type]
            if not is_valid:
                return Err(DataError(message=error or "Validation failed"))

        # Generate path
        resource_type = options.resource_type if options else None
        resource_id = options.resource_id if options else None

        from lexigram.admin.services.storage.utils import generate_upload_path

        path = generate_upload_path(
            filename,
            resource_type=resource_type,
            resource_id=resource_id,
            base_path=self.config.base_path,
        )

        try:
            # Compute SHA-256 hash for bytes content
            sha256_hash: str | None = None
            if isinstance(data, bytes):
                sha256_hash = hashlib.sha256(data).hexdigest()

            # Upload to storage
            upload_options = options.to_storage_options() if options else None
            if (
                sha256_hash
                and upload_options is not None
                and hasattr(upload_options, "metadata")
            ):
                upload_options.metadata = {  # type: ignore[misc]
                    **(upload_options.metadata or {}),
                    "sha256": sha256_hash,
                }
            result = await self._store.upload(path, data, upload_options)  # type: ignore[arg-type]

            # Convert to AdminFileInfo if needed
            file_info: AdminFileInfo
            if isinstance(result, AdminFileInfo):
                file_info = result
            elif FileInfo and isinstance(result, FileInfo):  # type: ignore[truthy-function]
                file_info = AdminFileInfo(
                    path=result.path,
                    size=result.size,
                    content_type=result.content_type,
                    last_modified=result.last_modified,
                    etag=result.etag,
                    metadata=result.metadata,
                )
            else:
                file_info = AdminFileInfo(
                    path=path,
                    size=len(data) if isinstance(data, bytes) else 0,
                    content_type=get_content_type(filename),
                    last_modified=datetime.now(UTC),
                )

            # Add admin metadata
            file_info.uploaded_by = uploaded_by
            file_info.resource_type = resource_type
            file_info.resource_id = resource_id

            return Ok(file_info)
        except (RuntimeError, OSError, ConnectionError) as e:
            return Err(DataError(message=str(e), original_error=e))

    async def download(self, path: str) -> bytes:
        """Download file content.

        Args:
            path: Storage path

        Returns:
            File content as bytes
        """
        return await self._store.download(path)

    async def delete(self, path: str) -> bool:
        """Delete a file.

        Args:
            path: Storage path

        Returns:
            True if deleted
        """
        try:
            await self._store.delete(path)
            return True
        except (RuntimeError, OSError):
            return False

    async def exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: Storage path

        Returns:
            True if exists
        """
        return await self._store.exists(path)

    async def get_download_url(
        self,
        path: str,
        expires_in: int | None = None,
    ) -> str:
        """Get presigned download URL.

        Args:
            path: Storage path
            expires_in: URL expiry in seconds

        Returns:
            Presigned URL
        """
        from datetime import timedelta

        expires_seconds = expires_in or self.config.presigned_url_expiry
        try:
            return await self._store.get_presigned_url(
                path,
                expires_in=timedelta(seconds=expires_seconds),
                method="GET",
            )
        except StorageUnsupportedOperationError:
            logger.warning(
                "storage.presigned_fallback_to_public",
                path=path,
                method="GET",
            )
            return await self._store.get_url(path)

    async def get_upload_url(
        self,
        filename: str,
        content_type: str | None = None,
        expires_in: int | None = None,
        resource_type: str | None = None,
        resource_id: Any = None,
    ) -> tuple[str, str]:
        """Get presigned upload URL for direct uploads.

        Allows clients to upload directly to storage without
        going through the server.

        Args:
            filename: Target filename

        Returns:
            Tuple of (presigned_url, storage_path)
        """
        from datetime import timedelta

        expires_seconds = expires_in or self.config.presigned_url_expiry

        from lexigram.admin.services.storage.utils import generate_upload_path

        path = generate_upload_path(
            filename,
            resource_type=resource_type,
            resource_id=resource_id,
            base_path=self.config.base_path,
        )

        try:
            url = await self._store.get_presigned_url(
                path,
                expires_in=timedelta(seconds=expires_seconds),
                method="PUT",
            )
        except StorageUnsupportedOperationError:
            logger.warning(
                "storage.presigned_fallback_to_public",
                path=path,
                method="PUT",
            )
            url = await self._store.get_url(path)

        return url, path
