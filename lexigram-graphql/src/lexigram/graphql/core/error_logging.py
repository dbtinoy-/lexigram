"""Structured error logging for GraphQL.

This module provides structured logging for GraphQL errors
to support debugging and monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import traceback
from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ErrorLogEntry:
    """Structured error log entry.

    Attributes:
        timestamp: When the error occurred.
        error_type: Type of the error.
        message: Error message.
        query: GraphQL query (may be masked).
        variables: Query variables (may be masked).
        path: Path in the GraphQL document.
        extensions: Error extensions.
        stacktrace: Exception stacktrace.
        context: Additional context.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_type: str = ""
    message: str = ""
    query: str | None = None
    variables: dict[str, Any] | None = None
    path: list[str] | None = None
    extensions: dict[str, Any] = field(default_factory=dict)
    stacktrace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "message": self.message,
            "query": self.query,
            "variables": self.variables,
            "path": self.path,
            "extensions": self.extensions,
            "stacktrace": self.stacktrace,
            "context": self.context,
        }


class ErrorLogger:
    """Structured error logger for GraphQL.

    Example:
        ```python
        logger = ErrorLogger()

        # Log an error
        logger.log_error(
            error=exc,
            query="{ user { name } }",
            variables={"id": "1"},
        )
        ```
    """

    def __init__(
        self,
        log_queries: bool = True,
        log_variables: bool = False,
        log_stacktrace: bool = True,
        max_query_length: int = 500,
    ):
        """Initialize the error logger.

        Args:
            log_queries: Whether to log queries.
            log_variables: Whether to log query variables.
            log_stacktrace: Whether to log stack traces.
            max_query_length: Maximum query length to log.
        """
        self._log_queries = log_queries
        self._log_variables = log_variables
        self._log_stacktrace = log_stacktrace
        self._max_query_length = max_query_length

    def log_error(
        self,
        error: Exception,
        query: str | None = None,
        variables: dict[str, Any] | None = None,
        path: list[str] | None = None,
        extensions: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ErrorLogEntry:
        """Log a GraphQL error.

        Args:
            error: The exception that occurred.
            query: The GraphQL query.
            variables: Query variables.
            path: Path in the GraphQL document.
            extensions: Error extensions.
            context: Additional context.

        Returns:
            The created log entry.
        """
        # Build the entry
        entry = ErrorLogEntry(
            error_type=type(error).__name__,
            message=str(error),
            path=path,
            extensions=extensions or {},
            context=context or {},
        )

        # Mask query if needed
        if query and self._log_queries:
            entry.query = query[: self._max_query_length]

        # Mask variables if needed
        if variables and self._log_variables:
            entry.variables = variables
        elif variables:
            # Mask sensitive variables
            entry.variables = self._mask_variables(variables)

        # Add stacktrace if needed
        if self._log_stacktrace:
            entry.stacktrace = traceback.format_exc()

        # Log the error
        logger.error(
            "GraphQL error: %s: %s",
            entry.error_type,
            entry.message,
            extra=entry.to_dict(),
        )

        return entry

    def _mask_variables(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive variables.

        Args:
            variables: Variables to mask.

        Returns:
            Masked variables.
        """
        sensitive_keys = {"password", "secret", "token", "api_key", "credit_card"}

        masked = {}
        for key, value in variables.items():
            if any(s in key.lower() for s in sensitive_keys):
                masked[key] = "***REDACTED***"
            else:
                masked[key] = value

        return masked


class QueryLogger:
    """Structured logger for GraphQL queries.

    Logs queries with timing and metadata for monitoring.
    """

    def __init__(self, enabled: bool = True):
        """Initialize the query logger.

        Args:
            enabled: Whether logging is enabled.
        """
        self._enabled = enabled

    def log_query(
        self,
        query: str,
        variables: dict | None = None,
        operation_name: str | None = None,
        duration_ms: float | None = None,
        errors_count: int = 0,
    ) -> None:
        """Log a GraphQL query.

        Args:
            query: The GraphQL query.
            variables: Query variables.
            operation_name: Name of the operation.
            duration_ms: Query duration in milliseconds.
            errors_count: Number of errors.
        """
        if not self._enabled:
            return

        # Determine operation type
        operation_type = self._extract_operation_type(query)

        # Build log data
        log_data = {
            "query": query[:500],  # Truncate for logging
            "operation_type": operation_type,
            "operation_name": operation_name,
            "variables": variables,
            "duration_ms": duration_ms,
            "errors_count": errors_count,
        }

        # Log based on errors
        if errors_count > 0:
            logger.warning(
                "GraphQL query completed with errors: %s, duration: %sms",
                operation_type,
                duration_ms,
                extra=log_data,
            )
        else:
            logger.info(
                "GraphQL query completed: %s, duration: %sms",
                operation_type,
                duration_ms,
                extra=log_data,
            )

    def _extract_operation_type(self, query: str) -> str:
        """Extract the operation type from a query.

        Args:
            query: GraphQL query string.

        Returns:
            Operation type (query, mutation, subscription).
        """
        query_lower = query.strip().lower()

        if query_lower.startswith("mutation"):
            return "mutation"
        if query_lower.startswith("subscription"):
            return "subscription"
        return "query"


# Default logger instance
default_error_logger = ErrorLogger()
default_query_logger = QueryLogger()


__all__ = [
    "ErrorLogEntry",
    "ErrorLogger",
    "QueryLogger",
    "default_error_logger",
    "default_query_logger",
]
