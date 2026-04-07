"""Storage drivers.

Core drivers (always available):
    - :class:`LocalDriver` — local filesystem storage
    - :class:`MemoryDriver` — in-memory storage for testing

Cloud drivers (requires optional dependencies):
    - :class:`S3Driver` — AWS S3 / compatible (install: ``pip install aiobotocore``)
    - :class:`GCSDriver` — Google Cloud Storage (install: ``pip install google-cloud-storage``)
    - :class:`AzureDriver` — Azure Blob Storage (install: ``pip install azure-storage-blob``)
"""

from __future__ import annotations

from lexigram.storage.backends.base import AbstractDriver
from lexigram.storage.backends.local import LocalDriver
from lexigram.storage.backends.memory import MemoryDriver

__all__ = ["AbstractDriver", "LocalDriver", "MemoryDriver"]

# ── Cloud drivers — optional dependencies ─────────────────────────────────


from lexigram.storage.backends.unavailable import _make_unavailable_class

try:
    from lexigram.storage.backends.s3 import S3Driver as S3Driver

    __all__.append("S3Driver")
except ImportError:
    S3Driver = _make_unavailable_class(  # type: ignore[assignment,misc]
        "S3Driver",
        "pip install aiobotocore",
    )

try:
    from lexigram.storage.backends.gcs import GCSDriver as GCSDriver

    __all__.append("GCSDriver")
except ImportError:
    GCSDriver = _make_unavailable_class(  # type: ignore[assignment,misc]
        "GCSDriver",
        "pip install google-cloud-storage",
    )

try:
    from lexigram.storage.backends.azure import AzureDriver as AzureDriver

    __all__.append("AzureDriver")
except ImportError:
    AzureDriver = _make_unavailable_class(  # type: ignore[assignment,misc]
        "AzureDriver",
        "pip install azure-storage-blob",
    )
