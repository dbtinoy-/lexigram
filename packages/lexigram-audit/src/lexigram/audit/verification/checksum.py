"""HMAC-SHA256 checksum computation and verification for audit entries."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import lexigram.serialization as json

__all__ = [
    "SCHEMA_VERSION_FIELD",
    "canonicalize_entry",
    "compute_audit_checksum",
    "verify_audit_checksum",
]


def canonicalize_entry(entry_data: dict[str, Any]) -> str:
    """Return canonical JSON string with sorted keys and compact separators.

    Args:
        entry_data: Dictionary of audit entry fields.

    Returns:
        Compact JSON string with sorted keys.
    """
    return json.dumps_str(
        entry_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


SCHEMA_VERSION_FIELD = "entry_schema_version"


def compute_audit_checksum(
    entry_data: dict[str, Any],
    key: bytes,
    schema_version: int = 2,
) -> str:
    """Compute HMAC-SHA256 hex digest for audit entry data.

    Includes ``entry_schema_version`` in the canonical form so the verifier
    knows which fields were expected at write time.

    Args:
        entry_data: Dictionary of audit entry fields.
        key: HMAC secret key bytes.
        schema_version: Schema version to embed (default 2). Existing
            entries use 1; new entries use 2.

    Returns:
        Hex-encoded HMAC-SHA256 digest.
    """
    payload = canonicalize_entry(
        {**entry_data, SCHEMA_VERSION_FIELD: schema_version}
    ).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_audit_checksum(
    entry_data: dict[str, Any],
    key: bytes,
    expected: str,
    schema_version: int | None = None,
) -> bool:
    """Verify expected checksum matches computed checksum using constant-time comparison.

    When *schema_version* is ``None``, the version is extracted from
    ``entry_data`` (defaults to 1 if absent) so old entries verify
    against v1 checksums and new entries verify against v2.

    Args:
        entry_data: Dictionary of audit entry fields.
        key: HMAC secret key bytes.
        expected: Previously stored checksum hex string.
        schema_version: Explicit schema version override. When ``None``,
            extracted from entry_data or defaults to 1.

    Returns:
        True if checksum matches, False if tampered.
    """
    if schema_version is None:
        schema_version = entry_data.get(SCHEMA_VERSION_FIELD, 1)
    actual = compute_audit_checksum(entry_data, key, schema_version=schema_version)
    return hmac.compare_digest(actual, expected)
