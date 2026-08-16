"""Query depth limiting.

This module provides depth limiting for GraphQL queries
to prevent deeply nested queries that could impact performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.extensions import SchemaExtension

from lexigram.graphql.exceptions import QueryTooDeepError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from graphql.language.ast import (
        DocumentNode,
        FragmentDefinitionNode,
        SelectionSetNode,
    )


logger = get_logger(__name__)


class DepthLimitValidator:
    """Validate query depth against a limit.

    Analyzes GraphQL queries to determine their depth and
    validates against a configured maximum depth.

    Example:
        ```python
        validator = DepthLimitValidator(max_depth=10)

        # Validate a parsed document
        depth = validator.get_depth(document)
        validator.validate(document)  # Raises if too deep
        ```
    """

    def __init__(
        self,
        max_depth: int = 10,
        ignore_introspection: bool = True,
    ) -> None:
        """Initialize the validator.

        Args:
            max_depth: Maximum allowed query depth.
            ignore_introspection: Skip depth check for introspection queries.
        """
        self._max_depth = max_depth
        self._ignore_introspection = ignore_introspection

    @property
    def max_depth(self) -> int:
        """Get maximum depth limit."""
        return self._max_depth

    def get_depth(self, document: DocumentNode) -> int:
        """Calculate the maximum depth of a query.

        Args:
            document: Parsed GraphQL document.

        Returns:
            Maximum depth of the query.
        """
        max_depth = 0

        for definition in document.definitions:
            if hasattr(definition, "selection_set"):
                depth = self._calculate_depth(definition.selection_set, 0, document)
                max_depth = max(max_depth, depth)

        return max_depth

    def _calculate_depth(
        self,
        selection_set: SelectionSetNode | None,
        current_depth: int,
        document: DocumentNode | None = None,
        *,
        _visited_fragments: frozenset[str] | None = None,
    ) -> int:
        """Recursively calculate depth, traversing fragment spreads.

        Handles three AST node types:
        - ``Field``: increments depth and recurses into its selection set.
        - ``InlineFragment``: transparent wrapper; recurses at the same depth.
        - ``FragmentSpread``: looks up the named fragment definition from
          *document* and recurses at the same depth.  Already-visited
          fragment names are tracked via *_visited_fragments* to prevent
          infinite recursion from cyclically-defined fragments.

        Args:
            selection_set: Selection set to analyze.
            current_depth: Current depth level.
            document: Full parsed document, required for ``FragmentSpread``
                resolution.  Pass ``None`` only in contexts where the document
                is unavailable — fragment spreads will then be skipped.
            _visited_fragments: Names of fragments already being traversed in
                the current call chain (cycle guard).

        Returns:
            Maximum depth from this point.
        """
        if selection_set is None:
            return current_depth

        from graphql.language.ast import (
            FragmentDefinitionNode,
            FragmentSpreadNode,
            InlineFragmentNode,
        )

        visited = _visited_fragments or frozenset()
        max_depth = current_depth

        for selection in selection_set.selections:
            # Skip introspection fields early
            if self._ignore_introspection and hasattr(selection, "name"):
                name = (
                    selection.name.value
                    if hasattr(selection.name, "value")
                    else str(selection.name)
                )
                if name.startswith("__"):
                    continue

            if isinstance(selection, FragmentSpreadNode):
                # FragmentSpread: locate the named fragment and recurse.
                # The spread itself does not add a depth level — only the
                # fields inside the fragment do.
                if document is None:
                    continue
                frag_name = selection.name.value
                if frag_name in visited:
                    continue  # cycle guard
                frag_def: FragmentDefinitionNode | None = next(
                    (
                        d
                        for d in document.definitions
                        if isinstance(d, FragmentDefinitionNode)
                        and d.name.value == frag_name
                    ),
                    None,
                )
                if frag_def is not None:
                    depth = self._calculate_depth(
                        frag_def.selection_set,
                        current_depth,
                        document,
                        _visited_fragments=visited | {frag_name},
                    )
                    max_depth = max(max_depth, depth)

            elif isinstance(selection, InlineFragmentNode):
                # InlineFragment: transparent type guard; recurse at same depth.
                if selection.selection_set:
                    depth = self._calculate_depth(
                        selection.selection_set,
                        current_depth,
                        document,
                        _visited_fragments=visited,
                    )
                    max_depth = max(max_depth, depth)

            elif hasattr(selection, "selection_set") and selection.selection_set:
                # Field: increment depth for each nested selection set.
                depth = self._calculate_depth(
                    selection.selection_set,
                    current_depth + 1,
                    document,
                    _visited_fragments=visited,
                )
                max_depth = max(max_depth, depth)

        return max_depth

    def validate(self, document: DocumentNode) -> None:
        """Validate query depth.

        Args:
            document: Parsed GraphQL document.

        Raises:
            DepthLimitError: If query exceeds depth limit.
        """
        depth = self.get_depth(document)

        if depth > self._max_depth:
            raise QueryTooDeepError(
                f"Query depth {depth} exceeds maximum allowed depth of {self._max_depth}",
            )

        logger.debug("Query depth %d is within limit %d", depth, self._max_depth)


class DepthLimitExtension(SchemaExtension):
    """Strawberry extension for query depth limiting.

    Add this extension to your schema to automatically
    validate query depth before execution.

    Example:
        ```python
        from lexigram.graphql.security import DepthLimitExtension

        schema = strawberry.Schema(
            query=Query,
            extensions=[DepthLimitExtension(max_depth=10)],
        )
        ```
    """

    def __init__(
        self,
        max_depth: int = 10,
        ignore_introspection: bool = True,
    ) -> None:
        """Initialize the extension.

        Args:
            max_depth: Maximum allowed query depth.
            ignore_introspection: Skip introspection queries.
        """
        self._validator = DepthLimitValidator(
            max_depth=max_depth,
            ignore_introspection=ignore_introspection,
        )

    def on_validate(self) -> Iterator[None]:
        """Hook called during operation validation."""
        execution_context = self.execution_context

        # Validate depth
        if execution_context.graphql_document:
            try:
                self._validator.validate(execution_context.graphql_document)
            except QueryTooDeepError as e:
                logger.warning("Query rejected: %s", e)
                raise

        yield


def create_depth_limit(
    max_depth: int = 10,
    ignore_introspection: bool = True,
) -> DepthLimitExtension:
    """Create a depth limit extension (convenience function).

    Args:
        max_depth: Maximum allowed depth.
        ignore_introspection: Skip introspection queries.

    Returns:
        Configured extension.

    Example:
        ```python
        schema = strawberry.Schema(
            query=Query,
            extensions=[create_depth_limit(5)],
        )
        ```
    """
    return DepthLimitExtension(
        max_depth=max_depth,
        ignore_introspection=ignore_introspection,
    )


__all__ = [
    "DepthLimitExtension",
    "DepthLimitValidator",
    "create_depth_limit",
]
