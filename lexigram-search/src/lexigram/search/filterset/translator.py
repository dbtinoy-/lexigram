"""FilterSet → SearchQuery translator.

Converts an admin-facing :class:`~lexigram.search.filterset.types.FilterSet`
into a :class:`~lexigram.search.engine.SearchQuery` ready for execution
by any registered search backend.

The translation is performed by mapping each
:class:`~lexigram.search.filterset.types.FilterCondition` to its corresponding
:class:`~lexigram.search.query.types.QueryOperator` and delegating to the
:class:`~lexigram.search.query.builder.SearchQueryBuilder` for consistent
filter compilation.
"""

from __future__ import annotations

from lexigram.search.engine import SearchQuery
from lexigram.search.filterset.types import FilterCondition, FilterOperator, FilterSet
from lexigram.search.query.builder import SearchQueryBuilder
from lexigram.search.query.types import QueryOperator, SortDirection

# Mapping from admin-facing FilterOperator → internal QueryOperator.
# IS_NULL and IS_NOT_NULL are NOT in this map; they are handled via dedicated
# builder methods (where_null / where_not_null) that carry different semantics
# than a simple field/value filter.
_OPERATOR_MAP: dict[FilterOperator, QueryOperator] = {
    FilterOperator.EQ: QueryOperator.EQUAL,
    FilterOperator.NEQ: QueryOperator.NOT_EQUAL,
    FilterOperator.GT: QueryOperator.GREATER_THAN,
    FilterOperator.GTE: QueryOperator.GREATER_EQUAL,
    FilterOperator.LT: QueryOperator.LESS_THAN,
    FilterOperator.LTE: QueryOperator.LESS_EQUAL,
    FilterOperator.IN: QueryOperator.IN,
    FilterOperator.NOT_IN: QueryOperator.NOT_IN,
    FilterOperator.CONTAINS: QueryOperator.CONTAINS,
    FilterOperator.STARTS_WITH: QueryOperator.STARTS_WITH,
    FilterOperator.ENDS_WITH: QueryOperator.ENDS_WITH,
}


class FilterSetTranslator:
    """Translates a :class:`FilterSet` into a :class:`SearchQuery`.

    All conditions in the ``FilterSet`` are composed with AND semantics —
    a document must satisfy every condition to appear in results.

    Example::

        from lexigram.search.filterset import FilterCondition, FilterOperator, FilterSet
        from lexigram.search.filterset import FilterSetTranslator

        fs = FilterSet(
            conditions=(
                FilterCondition("status", FilterOperator.EQ, "active"),
                FilterCondition("score", FilterOperator.GTE, 80),
            ),
            order_by="name",
            order_dir="asc",
            page=2,
            page_size=10,
            search_query="python",
        )

        translator = FilterSetTranslator()
        search_query = translator.translate(fs)
    """

    def translate(self, filter_set: FilterSet) -> SearchQuery:
        """Translate *filter_set* to a :class:`SearchQuery`.

        Args:
            filter_set: The admin-facing filter specification to convert.

        Returns:
            A :class:`SearchQuery` ready to pass to a search engine.

        Raises:
            ValueError: If a :class:`FilterCondition` carries an operator that
                cannot be mapped (should not happen with valid enum values).
        """
        builder = SearchQueryBuilder()

        if filter_set.search_query:
            builder.query(filter_set.search_query)

        for condition in filter_set.conditions:
            _apply_condition(builder, condition)

        if filter_set.order_by:
            direction = (
                SortDirection.ASC
                if filter_set.order_dir.lower() == "asc"
                else SortDirection.DESC
            )
            builder.order_by(filter_set.order_by, direction)

        builder.page(filter_set.page, filter_set.page_size)

        return builder.build()


def _apply_condition(builder: SearchQueryBuilder, condition: FilterCondition) -> None:
    """Apply a single :class:`FilterCondition` to *builder*."""
    if condition.operator == FilterOperator.IS_NULL:
        builder.where_null(condition.field)
    elif condition.operator == FilterOperator.IS_NOT_NULL:
        builder.where_not_null(condition.field)
    else:
        query_op = _OPERATOR_MAP.get(condition.operator)
        if query_op is None:
            raise ValueError(
                f"FilterOperator {condition.operator!r} has no QueryOperator mapping"
            )
        builder.where(condition.field, condition.value, query_op)


__all__ = ["FilterSetTranslator"]
