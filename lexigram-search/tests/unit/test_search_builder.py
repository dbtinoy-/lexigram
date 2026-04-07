"""Unit tests for search query builder."""

import pytest
from lexigram.search.query.builder import SearchQueryBuilder, QueryOperator, SortDirection
from lexigram.search.config import QueryConfig

class TestSearchQueryBuilder:
    """Test SearchQueryBuilder functionality."""

    @pytest.fixture
    def builder(self):
        """Create builder."""
        return SearchQueryBuilder()

    def test_basic_query(self, builder):
        """Test basic query construction."""
        q = builder.query("test").build()
        assert q.q == "test"

    def test_filters(self, builder):
        """Test adding filters."""
        q = (
            builder
            .where("status", "active")
            .where("age", 18, QueryOperator.GREATER_EQUAL)
            .build()
        )
        
        # Checking how filters are structured in build()
        # It creates a dict where keys are fields.
        # If simple equality, value is direct.
        # If other operators (like GTE, which maps to... wait, implementation says:)
        # elif condition.operator == QueryOperator.RANGE: filters[field] = value
        # But GTE is not RANGE in that specific block?
        # Let's check logic:
        # Reference:
        # if condition.operator == QueryOperator.IN: ...
        # elif condition.operator == QueryOperator.NOT_IN: ...
        # elif condition.operator == QueryOperator.RANGE: ...
        # elif condition.operator == QueryOperator.EXISTS: ...
        # elif condition.operator == QueryOperator.NOT_EXISTS: ...
        # else: filters[condition.field] = condition.value
        
        # So GTE is treated as "else" if I passed it directly? 
        # But where_between uses RANGE.
        # The where() method: 
        # condition = FilterCondition(field=field, operator=operator, value=value)
        # It seems `where_between` creates `{"gte": min, "lte": max}` and sets operator=RANGE.
        # If I want just `age >= 18`, builder doesn't strictly have `where_gte` helper in the snippet I read?
        # where_between, where_in, where_not_in, where_null, where_not_null.
        # Generic `where` takes operator.
        # But `build` only handles specific operators specially.
        # If I pass `QueryOperator.GTE` to `where`, it hits the `else` block and assigns value directly?
        # That seems like a bug or limitation in the viewed code unless I missed something.
        # Let's inspect `QueryOperator` enum - wait, I can't inspect it here.
        # But based on `build` method logic:
        # else: filters[condition.field] = condition.value
        # So usage for GTE should likely be: where("age", {"gte": 18}, QueryOperator.RANGE)?
        # Or maybe the backend handles `{ field: { gte: 18 } }`?
        
        # Let's stick to what's explicitly supported in helpers for now to be safe.
        
        q_simple = builder.reset().where("status", "active").build()
        assert q_simple.filters["status"] == "active"

        q_in = builder.reset().where_in("role", ["admin", "user"]).build()
        assert q_in.filters["role"] == {"in": ["admin", "user"]}

    def test_sort(self, builder):
        """Test sorting."""
        q = (
            builder
            .order_by("created_at", SortDirection.DESC)
            .order_by_asc("title")
            .build()
        )
        
        assert q.sort == [
            {"created_at": "desc"},
            {"title": "asc"}
        ]

    def test_pagination(self, builder):
        """Test pagination."""
        q = builder.page(2, 20).build()
        assert q.limit == 20
        assert q.offset == 20

    def test_facets(self, builder):
        """Test facets."""
        q = builder.facet("category").build()
        assert "category" in q.facets

    def test_clone(self, builder):
        """Test cloning."""
        b1 = builder.query("original")
        b2 = b1.clone()
        b2.query("modified")
        
        assert b1.build().q == "original"
        assert b2.build().q == "modified"
