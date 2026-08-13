"""Error formatting for GraphQL responses.

This module provides error masking and formatting based on configuration.
"""

from __future__ import annotations

import traceback
from typing import Any

from lexigram.graphql.config import ErrorConfig
from lexigram.graphql.exceptions import GraphQLError


def _is_safe_error(error: Exception) -> bool:
    """Check if an error is safe to show to users.

    Args:
        error: The error to check.

    Returns:
        True if the error message can be safely shown to users.
    """
    # Check for safe attribute on GraphQLError subclasses
    if isinstance(error, GraphQLError):
        return getattr(error, "safe", False)
    return False


class ErrorFormatter:
    """Format GraphQL errors for client consumption.

    Applies masking rules based on ErrorConfig to prevent
    internal errors from leaking to clients in production.
    """

    def __init__(self, config: ErrorConfig):
        """Initialize the error formatter.

        Args:
            config: Error configuration.
        """
        self._config = config

    def format_error(
        self,
        error: Exception,
    ) -> dict[str, Any]:
        """Format an error for the response.

        Args:
            error: The exception to format (GraphQLError or Strawberry ErrorExtension).

        Returns:
            Formatted error dictionary.
        """
        # Handle Strawberry's ErrorExtension type
        if hasattr(error, "message"):
            message = str(error.message)
        elif isinstance(error, GraphQLError):
            message = error.message
        else:
            message = str(error)

        result: dict[str, Any] = {"message": message}

        # Add extensions for error code if available
        if isinstance(error, GraphQLError):
            extensions: dict[str, Any] = {}

            if hasattr(error, "code") and error.code:
                extensions["code"] = error.code

            # Add details if available
            if hasattr(error, "details") and error.details:
                extensions["details"] = error.details

            # Add hint if available
            if hasattr(error, "hint") and error.hint:
                extensions["hint"] = error.hint

            if extensions:
                result["extensions"] = extensions
        elif hasattr(error, "extensions") and error.extensions:
            result["extensions"] = error.extensions

        # Mask internal errors in production (unless error is marked as safe)
        if self._config.mask_errors and not _is_safe_error(error):
            result["message"] = "Internal server error"
            # Clear extensions that might leak info
            if "extensions" in result:
                result["extensions"] = {"code": "INTERNAL_ERROR"}

        # Include stacktrace only in debug mode
        if self._config.include_stacktrace and self._config.debug_mode:
            if "extensions" not in result:
                result["extensions"] = {}
            result["extensions"]["stacktrace"] = traceback.format_exception(
                type(error),
                error,
                error.__traceback__,
            )

        return result

    def format_errors(
        self,
        errors: list[Exception],
    ) -> list[dict[str, Any]]:
        """Format multiple errors for the response.

        Args:
            errors: List of exceptions to format.

        Returns:
            List of formatted error dictionaries.
        """
        return [self.format_error(error) for error in errors]


# Default error formatter factory
def create_error_formatter(config: ErrorConfig | None = None) -> ErrorFormatter:
    """Create an ErrorFormatter with the given config.

    Args:
        config: Error configuration. Uses defaults if None.

    Returns:
        Configured ErrorFormatter.
    """
    return ErrorFormatter(config or ErrorConfig())


__all__ = [
    "ErrorFormatter",
    "create_error_formatter",
]
