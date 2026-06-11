"""Unit tests for the shared metadata field validator."""

from __future__ import annotations

import pytest

from lexigram.vector.filters.validation import validate_metadata_field

VALID_FIELDS = [
    "user_id",
    "category",
    "a.b",
    "page-2",
    "_private",
    "x" * 64,
]

INVALID_FIELDS = [
    "x' OR metadata->>'auth_scope' = 'attacker",
    "'",
    '"',
    "has space",
    "has\\backslash",
    "1leading_digit",
    "",
    "x" * 65,
]


class TestValidateMetadataField:
    @pytest.mark.parametrize("field", VALID_FIELDS)
    def test_valid_fields_pass(self, field: str) -> None:
        validate_metadata_field(field)

    @pytest.mark.parametrize("field", INVALID_FIELDS)
    def test_invalid_fields_raise(self, field: str) -> None:
        with pytest.raises(ValueError, match="Invalid metadata field name"):
            validate_metadata_field(field)
