"""Fluent search query builder."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data import FilterExpression
from lexigram.logging import get_logger
from lexigram.search.config import QueryConfig
from lexigram.search.engine import SearchQuery
from lexigram.search.query.types import (
    AggregationSpec,
    AutocompleteQuery,
    FilterCondition,
    FuzzyQuery,
    GeoDistanceFilter,
    QueryOperator,
    SortDirection,
    SortField,
)
from lexigram.search.types import SearchStrategy

logger = get_logger(__name__)


class SearchQueryBuilder:
    """Fluent search query builder"""

    def __init__(self, config: QueryConfig | None = None):
        self.config = config or QueryConfig(
            strategy=SearchStrategy.FUZZY,
            default_limit=20,
            max_limit=1000,
            enable_highlighting=True,
            enable_faceting=True,
            enable_aggregations=False,
            fuzzy_threshold=0.8,
        )
        self._query: str = ""
        self._filters: list[FilterCondition] = []
        self._filter_expressions: list[FilterExpression] = []
        self._sort: list[SortField] = []
        self._fields: list[str] | None = None
        self._facets: list[str] = []
        self._aggregations: list[AggregationSpec] = []
        self._highlight: dict[str, Any] | None = None
        self._limit: int = self.config.default_limit
        self._offset: int = 0
        self._boost_functions: list[dict[str, Any]] = []
        self._fuzzy_queries: list[FuzzyQuery] = []
        self._autocomplete_queries: list[AutocompleteQuery] = []
        self._geo_filters: list[GeoDistanceFilter] = []

    def query(self, q: str) -> SearchQueryBuilder:
        """Set search query"""
        self._query = q
        return self

    def where(
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUAL,
    ) -> SearchQueryBuilder:
        """Add filter condition"""
        condition = FilterCondition(field=field, operator=operator, value=value)
        self._filters.append(condition)
        return self

    def where_in(self, field: str, values: list[Any]) -> SearchQueryBuilder:
        """Add IN filter"""
        return self.where(field, values, QueryOperator.IN)

    def where_not_in(self, field: str, values: list[Any]) -> SearchQueryBuilder:
        """Add NOT IN filter"""
        return self.where(field, values, QueryOperator.NOT_IN)

    def where_between(
        self,
        field: str,
        min_value: Any,
        max_value: Any,
    ) -> SearchQueryBuilder:
        """Add range filter"""
        return self.where(
            field,
            {"gte": min_value, "lte": max_value},
            QueryOperator.RANGE,
        )

    def where_null(self, field: str) -> SearchQueryBuilder:
        """Add null check filter"""
        return self.where(field, None, QueryOperator.NOT_EXISTS)

    def filter_expr(self, expr: FilterExpression) -> SearchQueryBuilder:
        """Add a composable ``FilterExpression`` tree as a filter.

        Accepts the ``FilterExpression`` type from ``lexigram.contracts.data``
        (``AndExpression``, ``OrExpression``, ``NotExpression``, or a leaf
        ``FilterConditionNode``) enabling complex, nested filter logic that
        the flat ``where()`` API cannot express.
        """
        self._filter_expressions.append(expr)
        return self

    def where_not_null(self, field: str) -> SearchQueryBuilder:
        """Add not null check filter"""
        return self.where(field, None, QueryOperator.EXISTS)

    def order_by(
        self,
        field: str,
        direction: SortDirection = SortDirection.ASC,
    ) -> SearchQueryBuilder:
        """Add sort field"""
        sort_field = SortField(field=field, direction=direction)
        self._sort.append(sort_field)
        return self

    def order_by_asc(self, field: str) -> SearchQueryBuilder:
        """Add ascending sort"""
        return self.order_by(field, SortDirection.ASC)

    def order_by_desc(self, field: str) -> SearchQueryBuilder:
        """Add descending sort"""
        return self.order_by(field, SortDirection.DESC)

    def select(self, *fields: str) -> SearchQueryBuilder:
        """Specify fields to return"""
        self._fields = list(fields)
        return self

    def facet(self, field: str) -> SearchQueryBuilder:
        """Add facet field"""
        if self.config.enable_faceting:
            self._facets.append(field)
        return self

    def aggregate(
        self,
        name: str,
        agg_type: str,
        field: str | None = None,
        **kwargs: Any,
    ) -> SearchQueryBuilder:
        """Add aggregation"""
        agg = AggregationSpec(name=name, type=agg_type, field=field, **kwargs)
        self._aggregations.append(agg)
        return self

    def terms_agg(self, name: str, field: str, size: int = 10) -> SearchQueryBuilder:
        """Add terms aggregation"""
        return self.aggregate(name, "terms", field=field, size=size)

    def range_agg(
        self,
        name: str,
        field: str,
        ranges: list[dict[str, Any]],
    ) -> SearchQueryBuilder:
        """Add range aggregation"""
        return self.aggregate(name, "range", field=field, ranges=ranges)

    def highlight(
        self,
        fields: list[str] | None = None,
        pre_tag: str | None = None,
        post_tag: str | None = None,
    ) -> SearchQueryBuilder:
        """Configure highlighting"""
        if self.config.enable_highlighting:
            self._highlight = {
                "fields": fields or ["*"],
                "pre_tags": [pre_tag or "<em>"],
                "post_tags": [post_tag or "</em>"],
            }
        return self

    def limit(self, limit: int) -> SearchQueryBuilder:
        """Set result limit"""
        self._limit = min(limit, self.config.max_limit)
        return self

    def offset(self, offset: int) -> SearchQueryBuilder:
        """Set result offset"""
        self._offset = offset
        return self

    def page(self, page: int, per_page: int) -> SearchQueryBuilder:
        """Set page-based pagination"""
        self._limit = min(per_page, self.config.max_limit)
        self._offset = (page - 1) * self._limit
        return self

    def boost(self, field: str, factor: float) -> SearchQueryBuilder:
        """Add field boost"""
        boost_func = {"field_value_factor": {"field": field, "factor": factor}}
        self._boost_functions.append(boost_func)
        return self

    def fuzzy(
        self, field: str, value: str, fuzziness: int | str = "auto"
    ) -> SearchQueryBuilder:
        """Add fuzzy (approximate-match) query for the given field."""
        self._fuzzy_queries.append(
            FuzzyQuery(field=field, value=value, fuzziness=fuzziness)  # type: ignore[arg-type]
        )
        return self

    def autocomplete(self, field: str, prefix: str) -> SearchQueryBuilder:
        """Add prefix-based autocomplete query."""
        self._autocomplete_queries.append(AutocompleteQuery(field=field, prefix=prefix))
        return self

    def geo_distance(
        self, field: str, lat: float, lon: float, distance: str
    ) -> SearchQueryBuilder:
        """Add geo-distance filter restricting results to within *distance* of a point."""
        self._geo_filters.append(
            GeoDistanceFilter(field=field, lat=lat, lon=lon, distance=distance)
        )
        return self

    def date_histogram_agg(
        self, name: str, field: str, interval: str = "1d"
    ) -> SearchQueryBuilder:
        """Add a date-histogram aggregation as a convenience wrapper around aggregate()."""
        return self.aggregate(name, "date_histogram", field=field, interval=interval)

    def build(self) -> SearchQuery:
        """Build the search query"""
        from lexigram.search.query.operator_registry import get_query_operator_registry

        registry = get_query_operator_registry()
        filters = {}
        for condition in self._filters:
            filters.update(registry.apply_operator(condition))
        for expr in self._filter_expressions:
            filters.update(registry.compile(expr))

        # Convert sort to dict format
        sort = []
        for sort_field in self._sort:
            sort.append(
                {
                    sort_field.field: sort_field.direction.value,
                },
            )

        # Convert aggregations
        aggregations: dict[str, Any] = {}
        for agg in self._aggregations:
            agg_config: dict[str, Any] = {"type": agg.type}
            if agg.field:
                agg_config["field"] = agg.field
            if agg.size:
                agg_config["size"] = agg.size
            if agg.ranges:
                agg_config["ranges"] = agg.ranges
            if agg.interval:
                agg_config["interval"] = agg.interval
            aggregations[agg.name] = agg_config

        fuzzy_queries = [
            {"field": fq.field, "value": fq.value, "fuzziness": fq.fuzziness}
            for fq in self._fuzzy_queries
        ] or None
        autocomplete_queries = [
            {"field": aq.field, "prefix": aq.prefix}
            for aq in self._autocomplete_queries
        ] or None
        geo_filters = [
            {"field": gf.field, "lat": gf.lat, "lon": gf.lon, "distance": gf.distance}
            for gf in self._geo_filters
        ] or None

        return SearchQuery(
            q=self._query,
            filters=filters if filters else None,
            sort=sort if sort else None,
            limit=self._limit,
            offset=self._offset,
            fields=self._fields,
            facets=self._facets if self._facets else None,
            aggregations=aggregations if aggregations else None,
            highlight=self._highlight,
            fuzzy_queries=fuzzy_queries,
            autocomplete_queries=autocomplete_queries,
            geo_filters=geo_filters,
        )

    def reset(self) -> SearchQueryBuilder:
        """Reset builder to initial state"""
        self._query = ""
        self._filters.clear()
        self._filter_expressions.clear()
        self._sort.clear()
        self._fields = None
        self._facets.clear()
        self._aggregations.clear()
        self._highlight = None
        self._limit = self.config.default_limit
        self._offset = 0
        self._boost_functions.clear()
        self._fuzzy_queries.clear()
        self._autocomplete_queries.clear()
        self._geo_filters.clear()
        return self

    def clone(self) -> SearchQueryBuilder:
        """Create a copy of this builder"""
        clone = SearchQueryBuilder(self.config)
        clone._query = self._query
        clone._filters = self._filters.copy()
        clone._filter_expressions = self._filter_expressions.copy()
        clone._sort = self._sort.copy()
        clone._fields = self._fields.copy() if self._fields else None
        clone._facets = self._facets.copy()
        clone._aggregations = self._aggregations.copy()
        clone._highlight = self._highlight.copy() if self._highlight else None
        clone._limit = self._limit
        clone._offset = self._offset
        clone._boost_functions = self._boost_functions.copy()
        clone._fuzzy_queries = self._fuzzy_queries.copy()
        clone._autocomplete_queries = self._autocomplete_queries.copy()
        clone._geo_filters = self._geo_filters.copy()
        return clone


__all__ = ["SearchQueryBuilder"]
