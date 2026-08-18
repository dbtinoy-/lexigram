"""Tests for validation primitives."""

# ruff: noqa: I001

from __future__ import annotations

from dev.core.validation import (
    ReferenceStatus,
    validate_package_coverage,
    validate_reference,
)


def test_validate_package_coverage_fails_when_any_package_missing() -> None:
    validation = validate_package_coverage(
        discovered={"lexigram", "lexigram-admin"},
        covered={"lexigram"},
    )

    assert validation.success is False
    assert validation.missing_packages == {"lexigram-admin"}


def test_validate_reference_marks_missing_reference_as_suspect() -> None:
    result = validate_reference("missing.py", exists=False)

    assert result.status is ReferenceStatus.SUSPECT


def test_validate_reference_marks_existing_complete_reference_as_correct() -> None:
    result = validate_reference("present.py", exists=True, complete=True)

    assert result.status is ReferenceStatus.CORRECT


def test_validate_reference_marks_existing_incomplete_reference_as_incomplete() -> None:
    result = validate_reference("partial.py", exists=True, complete=False)

    assert result.status is ReferenceStatus.INCOMPLETE
