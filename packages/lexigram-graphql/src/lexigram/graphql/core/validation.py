"""GraphQL query validation.

This module provides validation utilities for GraphQL queries,
delegating depth and alias checks to the canonical security validators
in ``lexigram.graphql.security``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.graphql import constants as const
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from graphql.language.ast import DocumentNode


logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of query validation.

    Attributes:
        is_valid: Whether the query is valid.
        errors: List of validation errors.
        depth: Maximum query depth.
        field_count: Total number of fields.
        warnings: Non-fatal warnings.
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    depth: int = 0
    field_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)


class SchemaValidator:
    """Validate GraphQL schemas and queries.

    Provides comprehensive validation of GraphQL queries against the schema,
    delegating depth enforcement to :class:`~lexigram.graphql.security.depth.DepthLimitValidator`
    and alias enforcement to :class:`~lexigram.graphql.security.alias.AliasLimitValidator`.

    Example:
        ```python
        validator = SchemaValidator(schema)
        result = validator.validate_query(query)

        if not result.is_valid:
            for error in result.errors:
                logger.info("Validation error: %s", error)
        ```
    """

    def __init__(
        self,
        schema: Any,
        max_depth: int = 10,
        max_aliases: int = 10,
        max_complexity: int = const.DEFAULT_MAX_COMPLEXITY,
    ) -> None:
        """Initialize the validator.

        Args:
            schema: GraphQL schema.
            max_depth: Maximum query depth (delegated to DepthLimitValidator).
            max_aliases: Maximum number of aliases (delegated to AliasLimitValidator).
            max_complexity: Maximum query complexity (delegated to ComplexityAnalyzer).
        """
        from lexigram.graphql.security.alias import AliasLimitValidator
        from lexigram.graphql.security.complexity import ComplexityAnalyzer
        from lexigram.graphql.security.depth import DepthLimitValidator

        self._schema = schema
        self._depth_validator = DepthLimitValidator(max_depth=max_depth)
        self._alias_validator = AliasLimitValidator(max_aliases=max_aliases)
        self._complexity_analyzer = ComplexityAnalyzer(
            max_complexity=max_complexity,
        )

    def validate_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate a GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Query variables.

        Returns:
            Validation result.
        """
        from graphql import parse
        from graphql import validate as gql_validate

        result = ValidationResult()

        try:
            document = parse(query)

            # Validate against schema — unwrap Strawberry wrappers if needed
            schema = self._schema
            if hasattr(schema, "__dict__"):
                for attr in ("_schema", "schema", "graphql_schema"):
                    val = getattr(schema, attr, None)
                    if val and val.__class__.__name__ == "GraphQLSchema":
                        schema = val
                        break

            for error in gql_validate(schema, document):
                result.add_error(str(error))

            # Depth — delegate to DepthLimitValidator (single source of truth)
            depth = self._depth_validator.get_depth(document)
            result.depth = depth
            if depth > self._depth_validator.max_depth:
                result.add_error(
                    f"Query depth {depth} exceeds maximum allowed depth of "
                    f"{self._depth_validator.max_depth}",
                )

            # Alias count — delegate to AliasLimitValidator (single source of truth)
            alias_count = self._alias_validator.count_aliases(document)
            if alias_count > self._alias_validator.max_aliases:
                result.add_error(
                    f"Query has {alias_count} aliases, exceeding limit of "
                    f"{self._alias_validator.max_aliases}",
                )

            # Complexity — delegate to ComplexityAnalyzer (single source of truth)
            complexity_ok, complexity_result = self._complexity_analyzer.check(
                document, schema
            )
            if not complexity_ok:
                result.add_error(complexity_result.warnings[0])

            # Field count (informational only — no dedicated security validator needed)
            result.field_count = self._count_fields(document)

        except (ValueError, SyntaxError, TypeError) as e:
            result.add_error(f"Query parse error: {e}")
        except Exception as e:  # noqa: BLE001 — duck-type check for GraphQLSyntaxError which cannot be imported directly
            if e.__class__.__name__ == "GraphQLSyntaxError":
                result.add_error(f"Query parse error: {e}")
            else:
                raise

        return result

    def _count_fields(self, document: DocumentNode) -> int:
        """Count the total number of fields in a document.

        Args:
            document: Parsed GraphQL document.

        Returns:
            Total field count.
        """
        count = 0

        def _recurse(selection_set: Any) -> None:
            nonlocal count
            if selection_set is None:
                return
            for selection in selection_set.selections:
                if hasattr(selection, "name"):
                    count += 1
                if hasattr(selection, "selection_set"):
                    _recurse(selection.selection_set)

        for definition in document.definitions:
            if hasattr(definition, "selection_set"):
                _recurse(definition.selection_set)

        return count


def validate_query(
    schema: Any,
    query: str,
    variables: dict[str, Any] | None = None,
    max_depth: int = 10,
) -> ValidationResult:
    """Validate a GraphQL query (convenience function).

    Args:
        schema: GraphQL schema.
        query: GraphQL query string.
        variables: Query variables.
        max_depth: Maximum allowed depth.

    Returns:
        Validation result.
    """
    validator = SchemaValidator(schema, max_depth=max_depth)
    return validator.validate_query(query, variables)


__all__ = [
    "SchemaValidator",
    "ValidationResult",
    "validate_query",
]
