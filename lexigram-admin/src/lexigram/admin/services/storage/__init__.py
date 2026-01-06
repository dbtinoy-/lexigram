"""
Admin storage service package.

Provides components for file upload management in admin interfaces.
"""

from __future__ import annotations

from lexigram.admin.config import AdminStorageConfig
from lexigram.admin.services.storage.mixins import UploadHandlerProtocol
from lexigram.admin.services.storage.service import AdminStorageService
from lexigram.admin.services.storage.types import (
    AdminFileInfo,
    AdminUploadOptions,
    StorageDriver,
    UploadResult,
)
from lexigram.admin.services.storage.upload import (
    FileUploadService,
    FileValidator,
    StorageBackend,
    UploadedFile,
)
from lexigram.admin.services.storage.utils import generate_upload_path, get_content_type

__all__ = [
    "AdminFileInfo",
    "AdminStorageConfig",
    "AdminStorageService",
    "AdminUploadOptions",
    "FileUploadService",
    "FileValidator",
    "StorageBackend",
    "StorageDriver",
    "UploadHandlerProtocol",
    "UploadResult",
    "UploadedFile",
    "generate_upload_path",
    "get_content_type",
]
