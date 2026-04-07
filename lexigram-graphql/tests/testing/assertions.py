"""Test assertions for GraphQL.

This module provides assertion helpers for validating
GraphQL test results.
"""

from __future__ import annotations

from typing import Any

from lexigram.graphql.tests.testing.client import TestResult


def assert_no_errors(result: TestResult[Any]) -> None:
    """Assert that a result has no errors.

    Args:
        result: Test result to check.

    Raises:
        AssertionError: If result has errors.
    """
    if result.has_errors:
        messages = ", ".join(result.error_messages)
        raise AssertionError(f"Expected no errors, but got: {messages}")


def assert_has_errors(
    result: TestResult[Any],
    count: int | None = None,
) -> None:
    """Assert that a result has errors.

    Args:
        result: Test result to check.
        count: Expected number of errors (optional).

    Raises:
        AssertionError: If result has no errors or wrong count.
    """
    if not result.has_errors:
        raise AssertionError("Expected errors, but result was successful")

    if count is not None:
        actual_count = len(result.errors)
        if actual_count != count:
            raise AssertionError(
                f"Expected {count} errors, got {actual_count}: {result.error_messages}",
            )


def assert_data_equals(
    result: TestResult[Any],
    expected: Any,
    path: str | None = None,
) -> None:
    """Assert that result data equals expected value.

    Args:
        result: Test result to check.
        expected: Expected data value.
        path: Optional dot-notation path to nested value.

    Raises:
        AssertionError: If data doesn't match.
    """
    assert_no_errors(result)

    actual = result.data

    if path:
        for key in path.split("."):
            if isinstance(actual, dict):
                actual = actual.get(key)
            elif isinstance(actual, list) and key.isdigit():
                actual = actual[int(key)]
            else:
                raise AssertionError(
                    f"Cannot access path '{path}' in data: {result.data}",
                )

    if actual != expected:
        raise AssertionError(
            f"Expected data{' at ' + path if path else ''} to equal "
            f"{expected!r}, got {actual!r}",
        )


def assert_data_contains(
    result: TestResult[Any],
    expected: dict[str, Any],
) -> None:
    """Assert that result data contains expected keys/values.

    Args:
        result: Test result to check.
        expected: Expected key-value pairs.

    Raises:
        AssertionError: If data doesn't contain expected values.
    """
    assert_no_errors(result)

    if not isinstance(result.data, dict):
        raise AssertionError(f"Expected data to be a dict, got {type(result.data)}")

    for key, value in expected.items():
        if key not in result.data:
            raise AssertionError(
                f"Expected data to contain key '{key}', data: {result.data}",
            )
        if result.data[key] != value:
            raise AssertionError(
                f"Expected data['{key}'] to equal {value!r}, got {result.data[key]!r}",
            )


def assert_error_contains(
    result: TestResult[Any],
    message: str,
) -> None:
    """Assert that an error contains a message substring.

    Args:
        result: Test result to check.
        message: Expected message substring.

    Raises:
        AssertionError: If no error contains the message.
    """
    if not result.has_errors:
        raise AssertionError(
            f"Expected error containing '{message}', but result was successful",
        )

    for error_msg in result.error_messages:
        if message in error_msg:
            return

    raise AssertionError(
        f"Expected error containing '{message}', got errors: {result.error_messages}",
    )


def assert_error_code(
    result: TestResult[Any],
    code: str,
) -> None:
    """Assert that an error has a specific code in extensions.

    Args:
        result: Test result to check.
        code: Expected error code.

    Raises:
        AssertionError: If no error has the code.
    """
    if not result.has_errors:
        raise AssertionError(
            f"Expected error with code '{code}', but result was successful",
        )

    for error in result.errors:
        extensions = error.get("extensions", {})
        if extensions.get("code") == code:
            return

    raise AssertionError(
        f"Expected error with code '{code}', got errors: {result.errors}",
    )


def assert_field_in_data(
    result: TestResult[Any],
    field: str,
) -> Any:
    """Assert that a field exists in data and return it.

    Args:
        result: Test result to check.
        field: Field name or dot-notation path.

    Returns:
        The field value.

    Raises:
        AssertionError: If field doesn't exist.
    """
    assert_no_errors(result)

    value = result.data

    for key in field.split("."):
        if isinstance(value, dict):
            if key not in value:
                raise AssertionError(
                    f"Expected field '{field}' in data, data: {result.data}",
                )
            value = value[key]
        elif isinstance(value, list) and key.isdigit():
            idx = int(key)
            if idx >= len(value):
                raise AssertionError(f"Index {idx} out of range for field '{field}'")
            value = value[idx]
        else:
            raise AssertionError(
                f"Cannot access field '{field}' in data: {result.data}",
            )

    return value


def assert_list_length(
    result: TestResult[Any],
    path: str,
    length: int,
) -> None:
    """Assert that a list field has a specific length.

    Args:
        result: Test result to check.
        path: Dot-notation path to list field.
        length: Expected length.

    Raises:
        AssertionError: If list doesn't have expected length.
    """
    value = assert_field_in_data(result, path)

    if not isinstance(value, list):
        raise AssertionError(f"Expected field '{path}' to be a list, got {type(value)}")

    if len(value) != length:
        raise AssertionError(
            f"Expected list at '{path}' to have length {length}, got {len(value)}",
        )


__all__ = [
    "assert_data_contains",
    "assert_data_equals",
    "assert_error_code",
    "assert_error_contains",
    "assert_field_in_data",
    "assert_has_errors",
    "assert_list_length",
    "assert_no_errors",
]
