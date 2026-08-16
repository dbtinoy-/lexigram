"""Unit tests for safe query builder."""

import pytest
from lexigram.search.query.safe_query import (
    SafeQueryBuilder,
    SafeSearchQuery,
    ElasticsearchBackend,
    AlgoliaBackend
)

class TestElasticsearchBackend:
    """Test ES backend."""

    def test_escape(self):
        backend = ElasticsearchBackend()
        # "test+query" -> "test\+query"
        assert backend.escape("test+query") == "test\\+query"

    def test_build_term(self):
        backend = ElasticsearchBackend()
        q = SafeSearchQuery(query_type="term", field="id", value="123")
        result = backend.build(q)
        assert result == {"term": {"id": "123"}}

    def test_build_match(self):
        backend = ElasticsearchBackend()
        q = SafeSearchQuery(query_type="match", field="title", value="hello world")
        result = backend.build(q)
        assert result["match"]["title"]["query"] == "hello world"

class TestAlgoliaBackend:
    """Test Algolia backend."""

    def test_escape(self):
        backend = AlgoliaBackend()
        # 'quoted "value"' -> 'quoted \"value\"'
        assert backend.escape('quoted "value"') == 'quoted \\"value\\"'

    def test_build_match(self):
        backend = AlgoliaBackend()
        q = SafeSearchQuery(query_type="match", field="title", value="test")
        result = backend.build(q)
        assert result["query"] == "test"
        assert result["restrictSearchableAttributes"] == ["title"]

class TestSafeQueryBuilder:
    """Test builder API."""

    @pytest.fixture
    def builder(self):
        return SafeQueryBuilder(ElasticsearchBackend())

    def test_term(self, builder):
        q = builder.term("status", "active")
        assert q.query_type == "term"
        assert q.field == "status"
        assert q.value == "active"

    def test_match(self, builder):
        q = builder.match("description", "search text")
        assert q.query_type == "match"

    def test_range(self, builder):
        q = builder.range("price", gte=10, lte=20)
        assert q.query_type == "range"
        assert q.value == {"gte": 10, "lte": 20}

    def test_bool(self, builder):
        q1 = builder.term("status", "active")
        q2 = builder.range("age", gte=18)
        
        q = builder.bool("AND", q1, q2)
        assert q.query_type == "bool"
        assert q.operator == "AND"
        assert len(q.children) == 2

    def test_validate_field_unsafe(self, builder):
        with pytest.raises(ValueError):
            builder.term("unsafe;field", "value")
