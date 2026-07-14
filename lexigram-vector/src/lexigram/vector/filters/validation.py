"""Metadata field name validation for vector metadata filters."""

from __future__ import annotations

import re

_METADATA_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")


def validate_metadata_field(field: str) -> None:
    """Validate a metadata field name before it reaches a filter compiler.

    Rejects keys that could break out of the single-quoted JSONB literal
    used by the pgvector compiler (quotes, backslashes, spaces), and caps
    total length at 64 characters. Dots and hyphens are preserved because
    JSONB path/EXISTS operators take a literal string key.

    Args:
        field: Metadata field name to validate.

    Raises:
        ValueError: If the field does not match the identifier charset gate.
    """
    if not _METADATA_FIELD_RE.fullmatch(field):
        raise ValueError(f"Invalid metadata field name: {field!r}")
