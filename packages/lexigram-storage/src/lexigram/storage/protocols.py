"""Public protocol surface for ``lexigram.storage``."""

from __future__ import annotations

from lexigram.contracts.infra.storage import BlobStoreProtocol, StorageBackendProtocol
from lexigram.storage.backends.protocols import StreamingBodyProtocol

__all__ = [
    "BlobStoreProtocol",
    "StorageBackendProtocol",
    "StreamingBodyProtocol",
]
