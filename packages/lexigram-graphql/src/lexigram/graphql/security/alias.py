"""Query alias limiting.

This module provides alias limiting for GraphQL queries
to prevent abuse through excessive field aliasing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.extensions import SchemaExtension

from lexigram.graphql.exceptions import GraphQLError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from graphql.language.ast import DocumentNode, SelectionSetNode


logger = get_logger(__name__)


class AliasLimitValidator:
    """Validate query alias count against a limit.

    Analyzes GraphQL queries to count aliases and validates
    against a configured maximum.

    Example:
        ```python
        validator = AliasLimitValidator(max_aliases=10)

        count = validator.count_aliases(document)
        validator.validate(document)  # Raises if too many
        ```
    """

    def __init__(self, max_aliases: int = 10) -> None:
        """Initialize the validator.

        Args:
            max_aliases: Maximum allowed aliases.
        """
        self._max_aliases = max_aliases

    @property
    def max_aliases(self) -> int:
        """Get maximum alias limit."""
        return self._max_aliases

    def count_aliases(self, document: DocumentNode) -> int:
        """Count the number of aliases in a query.

        Args:
            document: Parsed GraphQL document.

        Returns:
            Number of aliases.
        """
        count = 0

        for definition in document.definitions:
            if hasattr(definition, "selection_set"):
                count += self._count_in_selection_set(definition.selection_set)

        return count

    def _count_in_selection_set(
        self,
        selection_set: SelectionSetNode | None,
    ) -> int:
        """Count aliases in a selection set.

        Args:
            selection_set: Selection set to analyze.

        Returns:
            Number of aliases.
        """
        if selection_set is None:
            return 0

        count = 0

        for selection in selection_set.selections:
            # Check for alias
            if hasattr(selection, "alias") and selection.alias:
                count += 1

            # Recurse into nested selections
            if hasattr(selection, "selection_set"):
                count += self._count_in_selection_set(selection.selection_set)

        return count

    def validate(self, document: DocumentNode) -> None:
        """Validate alias count.

        Args:
            document: Parsed GraphQL document.

        Raises:
            SecurityError: If query has too many aliases.
        """
        count = self.count_aliases(document)

        if count > self._max_aliases:
            error = GraphQLError(
                f"Query has {count} aliases, exceeding maximum of {self._max_aliases}",
            )
            error.safe = True
            raise error

        logger.debug("Query has %d aliases (limit: %d)", count, self._max_aliases)


class AliasLimitExtension(SchemaExtension):
    """Strawberry extension for query alias limiting.

    Add this extension to your schema to automatically
    validate alias count before execution.

    Example:
        ```python
        from lexigram.graphql.security import AliasLimitExtension

        schema = strawberry.Schema(
            query=Query,
            extensions=[AliasLimitExtension(max_aliases=10)],
        )
        ```
    """

    def __init__(self, max_aliases: int = 10) -> None:
        """Initialize the extension.

        Args:
            max_aliases: Maximum allowed aliases.
        """
        self._validator = AliasLimitValidator(max_aliases=max_aliases)

    def on_validate(self) -> Iterator[None]:
        """Hook called during operation validation."""
        execution_context = self.execution_context

        # Validate alias count
        if execution_context.graphql_document:
            self._validator.validate(execution_context.graphql_document)

        yield


__all__ = ["AliasLimitExtension", "AliasLimitValidator"]
