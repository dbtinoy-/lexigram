"""Query complexity analysis for GraphQL.

This module provides complexity scoring to prevent expensive queries
from being executed. Fields can be annotated with costs, and lists
can be multiplied based on pagination arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from graphql import GraphQLSchema
    from graphql.language.ast import DocumentNode, SelectionSetNode

logger = get_logger(__name__)


# G-27 FIX:
# Registry keyed by the *resolver function name* (which maps to the GraphQL field name
# under Strawberry's default snake_to_camel convention) so that ComplexityAnalyzer can
# look up costs purely from the query's field names.
#
# Keys are lowercase function names; callers must register consistently.
_FIELD_COSTS_BY_NAME: dict[str, float] = {}
_LIST_COST_MULTIPLIERS_BY_NAME: dict[str, Callable[..., float]] = {}


def cost(value: float) -> Callable:
    """Decorator to set the cost of a field resolver.

    Sets ``func.__graphql_cost__`` on the resolver and registers the cost
    in the module-level lookup table keyed by ``func.__name__`` so that
    :class:`ComplexityAnalyzer` can resolve the cost from the GraphQL
    field name during query analysis.

    Args:
        value: The cost value for this field.

    Returns:
        Decorator function.

    Example:
        @cost(10)
        def resolve_expensive_field(self, info):
            return expensive_operation()
    """

    def decorator(func: Callable) -> Callable:
        func.__graphql_cost__ = value  # type: ignore[attr-defined]
        _FIELD_COSTS_BY_NAME[func.__name__] = value
        return func

    return decorator


def list_cost(multiplier: Callable[..., float]) -> Callable:
    """Decorator to set the cost multiplier for a list field.

    The multiplier function receives the field's arguments and should
    return a multiplier value based on pagination arguments.

    Sets ``func.__graphql_list_cost_multiplier__`` on the resolver and
    registers the multiplier in the module-level lookup table so that
    :class:`ComplexityAnalyzer` can use it from the field name.

    Args:
        multiplier: Function that calculates the list multiplier.

    Returns:
        Decorator function.

    Example:
        @list_cost(lambda first=10, last=10, **_: (first or 10) * (last or 10))
        def resolve_list(self, info, **kwargs):
            return items
    """

    def decorator(func: Callable) -> Callable:
        func.__graphql_list_cost_multiplier__ = multiplier  # type: ignore[attr-defined]
        _LIST_COST_MULTIPLIERS_BY_NAME[func.__name__] = multiplier
        return func

    return decorator


@dataclass
class ComplexityResult:
    """Result of complexity analysis.

    Attributes:
        complexity: Total complexity score.
        field_count: Number of fields in the query.
        list_count: Number of list fields.
        warnings: Any warnings generated during analysis.
    """

    complexity: float = 0
    field_count: int = 0
    list_count: int = 0
    warnings: list[str] = field(default_factory=list)


class ComplexityAnalyzer:
    """Analyze and score query complexity.

    Calculates complexity scores based on:
    - Base cost per field (default: 1)
    - List cost multiplier (default: 10)
    - Field-level cost annotations (@cost decorator)
    - List pagination arguments (first/last)

    Example:
        analyzer = ComplexityAnalyzer(max_complexity=1000)
        result = analyzer.analyze(document, schema)

        if result.complexity > 1000:
            raise QueryTooComplexError(f"Query complexity {result.complexity} exceeds limit")
    """

    def __init__(
        self,
        max_complexity: int = 1000,
        default_field_cost: float = 1.0,
        default_list_cost: float = 10.0,
    ) -> None:
        """Initialize the analyzer.

        Args:
            max_complexity: Maximum allowed complexity score.
            default_field_cost: Default cost for a scalar field.
            default_list_cost: Default cost multiplier for list fields.
        """
        self._max_complexity = max_complexity
        self._default_field_cost = default_field_cost
        self._default_list_cost = default_list_cost

    @property
    def max_complexity(self) -> int:
        """Get maximum complexity limit."""
        return self._max_complexity

    def analyze(
        self,
        document: DocumentNode,
        schema: GraphQLSchema | None = None,
    ) -> ComplexityResult:
        """Analyze query complexity.

        Args:
            document: Parsed GraphQL document.
            schema: Optional GraphQL schema for type-aware analysis.

        Returns:
            Complexity result with score and metadata.
        """
        result = ComplexityResult()
        total_complexity = 0.0

        for definition in document.definitions:
            if hasattr(definition, "selection_set") and definition.selection_set:
                complexity = self._analyze_selection_set(
                    definition.selection_set,
                    result,
                    schema,
                    depth=0,
                )
                total_complexity += complexity

        result.complexity = total_complexity
        return result

    def _analyze_selection_set(
        self,
        selection_set: SelectionSetNode,
        result: ComplexityResult,
        schema: GraphQLSchema | None,
        depth: int,
    ) -> float:
        """Recursively analyze a selection set.

        Args:
            selection_set: The selection set to analyze.
            result: Result object to accumulate metrics.
            schema: Optional GraphQL schema.
            depth: Current depth in the query.

        Returns:
            Complexity score for this selection set.
        """
        total_cost = 0.0

        for selection in selection_set.selections:
            if not hasattr(selection, "name"):
                continue

            field_name = (
                selection.name.value
                if hasattr(selection.name, "value")
                else str(selection.name)
            )

            # Skip introspection fields
            if field_name.startswith("__"):
                continue

            # Check if this is a list field (has arguments like first, last)
            is_list = self._is_list_field(selection, schema)

            # Calculate base cost
            field_cost = self._get_field_cost(field_name, is_list)

            # Get list multiplier if applicable
            multiplier = 1.0
            if is_list:
                multiplier = self._get_list_multiplier(selection)
                result.list_count += 1

            # Calculate child complexity if there's a nested selection
            child_cost = 0.0
            if hasattr(selection, "selection_set") and selection.selection_set:
                child_cost = self._analyze_selection_set(
                    selection.selection_set,
                    result,
                    schema,
                    depth + 1,
                )

            # Combine costs
            field_total = (field_cost + child_cost) * multiplier
            total_cost += field_total
            result.field_count += 1

        return total_cost

    def _is_list_field(
        self,
        field_node: Any,
        schema: GraphQLSchema | None,
    ) -> bool:
        """Check if a field returns a list type.

        Args:
            field_node: The field node to check.
            schema: Optional schema for type info.

        Returns:
            True if the field returns a list.
        """
        # Check for pagination arguments commonly used with lists
        args: list[Any] = list(field_node.arguments or [])
        arg_names = {arg.name.value for arg in args}

        list_args = {"first", "last", "limit", "after", "before"}
        if list_args & arg_names:
            return True

        # If we have schema, we could check the return type
        # but for now, we'll rely on argument presence
        return False

    def _get_field_cost(self, field_name: str, is_list: bool = False) -> float:
        """Get the cost for a field.

        Checks the registry populated by the :func:`cost` decorator first,
        using ``field_name`` as the key (matching ``func.__name__``). Falls
        back to the configured default costs.

        Args:
            field_name: GraphQL field name.
            is_list: Whether the field returns a list.

        Returns:
            Cost value for the field.
        """
        # G-27 FIX: look up by field name in the decorator-populated registry.
        if field_name in _FIELD_COSTS_BY_NAME:
            return _FIELD_COSTS_BY_NAME[field_name]

        if is_list:
            return self._default_list_cost

        return self._default_field_cost

    def _get_list_multiplier(self, field_node: Any) -> float:
        """Get the multiplier for a list field based on its arguments.

        Args:
            field_node: The list field node.

        Returns:
            Multiplier value (defaults to 10 if no arguments found).
        """
        args: list[Any] = list(field_node.arguments or [])
        args_dict = {}
        for arg in args:
            if hasattr(arg, "value"):
                # Handle both name and value attributes
                arg_name = (
                    arg.name.value if hasattr(arg.name, "value") else str(arg.name)
                )
                if hasattr(arg.value, "value"):
                    args_dict[arg_name] = arg.value.value
                else:
                    args_dict[arg_name] = arg.value

        # Check for first/last/limit
        first = args_dict.get("first")
        last = args_dict.get("last")
        limit = args_dict.get("limit")

        if first is not None:
            return float(first)
        if last is not None:
            return float(last)
        if limit is not None:
            return float(limit)

        # Default multiplier if no pagination args
        return self._default_list_cost

    def check(
        self, document: DocumentNode, schema: GraphQLSchema | None = None
    ) -> tuple[bool, ComplexityResult]:
        """Check query complexity and return a detailed result.

        Unlike :meth:`validate`, this method never raises — it returns a
        ``(is_valid, result)`` tuple so callers can inspect the details.

        Args:
            document: Parsed GraphQL document.
            schema: Optional GraphQL schema.

        Returns:
            Tuple of (is_valid, result).
        """
        result = self.analyze(document, schema)
        is_valid = result.complexity <= self._max_complexity

        if not is_valid:
            result.warnings.append(
                f"Query complexity {result.complexity} exceeds maximum of {self._max_complexity}",
            )

        return is_valid, result

    def validate(
        self, document: DocumentNode, schema: GraphQLSchema | None = None
    ) -> None:
        """Validate query complexity; raise if the limit is exceeded.

        Conforms to :class:`~lexigram.contracts.graphql.ValidationRule` so
        instances of :class:`ComplexityAnalyzer` are usable wherever a
        validator is expected (alongside :class:`DepthLimitValidator` and
        :class:`AliasLimitValidator`).

        Args:
            document: Parsed GraphQL document.
            schema: Optional GraphQL schema.

        Raises:
            QueryTooComplexError: If the query exceeds :attr:`max_complexity`.
        """
        is_valid, result = self.check(document, schema)
        if not is_valid:
            from lexigram.graphql.exceptions import QueryTooComplexError

            msg = (
                result.warnings[0]
                if result.warnings
                else f"Query complexity {result.complexity} exceeds maximum of {self._max_complexity}"
            )
            raise QueryTooComplexError(msg)


# Convenience function for quick analysis
def analyze_complexity(
    query: str,
    max_complexity: int = 1000,
) -> ComplexityResult:
    """Analyze complexity of a GraphQL query.

    Args:
        query: GraphQL query string.
        max_complexity: Maximum allowed complexity.

    Returns:
        Complexity result.
    """
    from graphql import parse

    analyzer = ComplexityAnalyzer(max_complexity=max_complexity)
    document = parse(query)
    return analyzer.analyze(document)


__all__ = [
    "ComplexityAnalyzer",
    "ComplexityResult",
    "analyze_complexity",
    "cost",
    "list_cost",
]
