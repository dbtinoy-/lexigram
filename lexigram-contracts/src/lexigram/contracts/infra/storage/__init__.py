"""Storage protocols."""

from __future__ import annotations

from lexigram.contracts.infra.storage.kv import StorageBackendProtocol, StorageType
from lexigram.contracts.infra.storage.models import FileInfo, Uploadable, UploadOptions
from lexigram.contracts.infra.storage.protocols import (
    BlobStoreProtocol,
    StorageDriverProtocol,
    StorageProviderProtocol,
)

__all__ = [
    "BlobStoreProtocol",
    "FileInfo",
    "StorageBackendProtocol",
    "StorageDriverProtocol",
    "StorageProviderProtocol",
    "StorageType",
    "UploadOptions",
    "Uploadable",
]
