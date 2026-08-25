"""Blob-name/metadata helpers for the Azure Blob Storage driver.

Pure, SDK-free utilities extracted from
:mod:`lexigram.storage.backends.azure`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.infra.storage import Uploadable


async def to_bytes(data: Uploadable) -> bytes:
    """Coerce *data* to :class:`bytes` for upload."""
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    if hasattr(data, "read"):
        raw = data.read()
        return raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
    if hasattr(data, "__aiter__"):
        chunks: list[bytes] = []
        async for chunk in data:
            chunks.append(
                chunk.encode("utf-8") if isinstance(chunk, str) else bytes(chunk),
            )
        return b"".join(chunks)
    raise ValueError(f"Unsupported data type: {type(data)}")


def is_blob_not_found(exc: BaseException) -> bool:
    """Return ``True`` when *exc* represents a missing Azure blob (404)."""
    exc_str = str(exc)
    return "BlobNotFound" in exc_str or "404" in exc_str


def coerce_last_modified(value: Any) -> datetime:
    """Return *value* when it is a datetime, otherwise the current UTC time."""
    if isinstance(value, datetime):
        return value
    return datetime.now(UTC)
