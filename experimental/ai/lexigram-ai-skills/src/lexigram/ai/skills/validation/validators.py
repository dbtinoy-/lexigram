"""Custom validators for skill parameters."""

from __future__ import annotations

from typing import Any


def validate_non_empty_string(value: Any, name: str) -> list[str]:
    """Validate that *value* is a non-empty string.

    Args:
        value: Value to check.
        name: Parameter name for error messages.

    Returns:
        List of validation errors.
    """
    if not isinstance(value, str) or not value.strip():
        return [f"'{name}' must be a non-empty string"]
    return []


def validate_positive_int(value: Any, name: str) -> list[str]:
    """Validate that *value* is a positive integer.

    Args:
        value: Value to check.
        name: Parameter name for error messages.

    Returns:
        List of validation errors.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return [f"'{name}' must be a positive integer"]
    return []


def validate_range(
    value: Any,
    name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> list[str]:
    """Validate that *value* falls within a numeric range.

    Args:
        value: Value to check.
        name: Parameter name for error messages.
        minimum: Inclusive lower bound.
        maximum: Inclusive upper bound.

    Returns:
        List of validation errors.
    """
    errors: list[str] = []
    if minimum is not None and value < minimum:
        errors.append(f"'{name}' must be >= {minimum}")
    if maximum is not None and value > maximum:
        errors.append(f"'{name}' must be <= {maximum}")
    return errors
