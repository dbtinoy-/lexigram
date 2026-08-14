"""Upload handler protocol for resource controllers."""

from __future__ import annotations

from typing import Any, BinaryIO, Protocol

from lexigram.admin.exceptions import DataError
from lexigram.admin.services.storage.types import AdminFileInfo
from lexigram.result import Result


class UploadHandlerProtocol(Protocol):
    """Protocol for resource controllers that handle file uploads.

    Implement this protocol in controllers that need file upload capability.
    Inject ``AdminStorageService`` via DI and call ``storage.upload()`` directly.

    Example:
        class UserController(ResourceController):
            def __init__(self, storage: AdminStorageService):
                self.storage = storage

            async def upload_avatar(
                self, user_id: int, file: bytes, filename: str
            ) -> Result[AdminFileInfo, DataError]:
                from lexigram.admin.services.storage.types import AdminUploadOptions
                options = AdminUploadOptions(resource_type="users", resource_id=user_id)
                return await self.storage.upload(file, filename, options)
    """

    async def handle_upload(
        self,
        data: bytes | BinaryIO,
        filename: str,
        resource_type: str | None = None,
        resource_id: Any = None,
        allowed_types: list[str] | None = None,
        max_size: int | None = None,
        uploaded_by: Any = None,
    ) -> Result[AdminFileInfo, DataError]:
        """Handle a file upload.

        Args:
            data: File content as bytes or file-like object.
            filename: Original filename.
            resource_type: Resource type for storage path organization.
            resource_id: Resource identifier.
            allowed_types: Allowed MIME types.
            max_size: Maximum file size in bytes.
            uploaded_by: Uploading user identifier.

        Returns:
            Result containing AdminFileInfo on success, DataError on failure.
        """
        ...
