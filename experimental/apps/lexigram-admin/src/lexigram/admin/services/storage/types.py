"""
Type definitions for admin storage service.

Provides enums, dataclasses, and protocols for file storage operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from lexigram.contracts.infra.storage import UploadOptions


class StorageDriver(StrEnum):
    """Storage driver types."""

    LOCAL = "local"
    S3 = "s3"
    MEMORY = "memory"


@dataclass
class AdminFileInfo:
    """File information for admin uploads."""

    path: str
    """Storage path."""

    size: int
    """File size in bytes."""

    content_type: str
    """MIME content type."""

    last_modified: datetime
    """Last modification timestamp."""

    etag: str | None = None
    """ETag for caching."""

    metadata: dict[str, Any] | None = None
    """Additional metadata."""

    # Admin-specific
    uploaded_by: Any = None
    resource_type: str | None = None
    resource_id: Any = None


@dataclass
class UploadResult:
    """Payload of a successful file upload.

    Always carried inside ``Ok[UploadResult, AdminError]``.
    """

    file_info: AdminFileInfo | None = None
    url: str | None = None


@dataclass
class AdminUploadOptions:
    """Options for admin file uploads."""

    content_type: str | None = None
    metadata: dict[str, str] | None = None
    public: bool = False

    # Admin-specific
    resource_type: str | None = None
    resource_id: Any = None
    allowed_types: list[str] | None = None
    max_size: int | None = None  # bytes

    def to_storage_options(self) -> UploadOptions:
        """Convert to storage contract UploadOptions."""
        return UploadOptions(
            content_type=self.content_type,
            metadata=self.metadata,
            public=self.public,
        )
