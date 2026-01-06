"""Tests for QueryTranslator implementations."""
from __future__ import annotations

import pytest

from lexigram.search.backends.translate import (
    ElasticsearchQueryTranslator,
    PostgresQueryTranslator,
    QueryTranslator,
    TranslatedQuery,
)


class TestTranslatedQuery:
    """Tests for TranslatedQuery dataclass."""

    def test_create_translated_query(self) -> None:
        """Verify TranslatedQuery can be created with defaults."""
        tq = TranslatedQuery(query="SELECT *", params=[], options={})
        assert tq.query == "SELECT *"
        assert tq.params == []
        assert tq.options == {}
        assert tq.aggregations is None
        assert tq.highlights is None

    def test_create_translated_query_with_optional_fields(self) -> None:
        """Verify TranslatedQuery with aggregations and highlights."""
        tq = TranslatedQuery(
            query="SELECT *",
            params=["param1"],
            options={"limit": 10},
            aggregations={"facet": "query"},
            highlights={"field": {}},
        )
        assert tq.aggregations == {"facet": "query"}
        assert tq.highlights == {"field": {}}


class TestQueryTranslator:
    """Tests for QueryTranslator ABC."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Verify QueryTranslator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            QueryTranslator()

    def test_concrete_translator_requires_config(self) -> None:
        """Verify a concrete translator is created with empty config."""

        class ConcreteTranslator(QueryTranslator):
            def translate_search(self, query, filters=None, sort=None, limit=20, offset=0, **kwargs):
                return TranslatedQuery(query="test", params=[], options={})

            def translate_faceted_search(self, query, facets, filters=None, limit=20, offset=0, **kwargs):
                return TranslatedQuery(query="test", params=[], options={})

            def translate_highlight(self, fields, pre_tags=None, post_tags=None, **kwargs):
                return {}

        t = ConcreteTranslator()
        assert t.config == {}

        t_with_config = ConcreteTranslator({"key": "value"})
        assert t_with_config.config == {"key": "value"}


class TestPostgresQueryTranslator:
    """Tests for PostgresQueryTranslator."""

    @pytest.fixture
    def translator(self) -> PostgresQueryTranslator:
        return PostgresQueryTranslator(text_search_config="simple")

    def test_init_with_default_config(self) -> None:
        """Verify default text search config is english."""
        t = PostgresQueryTranslator()
        assert t.text_search_config == "english"

    def test_init_with_custom_config(self) -> None:
        """Verify custom text search config is applied."""
        t = PostgresQueryTranslator(text_search_config="simple")
        assert t.text_search_config == "simple"

    def test_translate_search_basic(self, translator: PostgresQueryTranslator) -> None:
        """Verify basic search translation."""
        result = translator.translate_search("test query")
        assert isinstance(result, TranslatedQuery)
        assert "websearch_to_tsquery" in result.query
        assert "simple" in str(result.params[0])
        assert "test query" in str(result.params[1])
        assert len(result.params) == 4  # config, query, limit, offset

    def test_translate_search_with_filters(self, translator: PostgresQueryTranslator) -> None:
        """Verify search with filters adds WHERE clause."""
        result = translator.translate_search("test", filters={"status": "active"})
        assert "document @> $" in result.query
        assert len(result.params) == 5  # config, query, filter_json, limit, offset

    def test_translate_search_with_sort_asc(self, translator: PostgresQueryTranslator) -> None:
        """Verify ascending sort is translated."""
        result = translator.translate_search("test", sort=["name"])
        assert "document->>'name' ASC" in result.query
        assert "ORDER BY" in result.query

    def test_translate_search_with_sort_desc(self, translator: PostgresQueryTranslator) -> None:
        """Verify descending sort is translated."""
        result = translator.translate_search("test", sort=["-name"])
        assert "document->>'name' DESC" in result.query
        assert "ORDER BY" in result.query

    def test_translate_search_default_order(self, translator: PostgresQueryTranslator) -> None:
        """Verify default sort is by score DESC."""
        result = translator.translate_search("test")
        assert "ORDER BY score DESC" in result.query

    def test_translate_search_pagination(self, translator: PostgresQueryTranslator) -> None:
        """Verify pagination is included."""
        result = translator.translate_search("test", limit=10, offset=5)
        assert "LIMIT" in result.query
        assert "OFFSET" in result.query
        assert result.options == {"limit": 10, "offset": 5}

    def test_translate_faceted_search(self, translator: PostgresQueryTranslator) -> None:
        """Verify faceted search adds aggregations."""
        result = translator.translate_faceted_search("test", ["category", "status"])
        assert result.aggregations is not None
        assert "category" in result.aggregations
        assert "status" in result.aggregations
        assert "GROUP BY" in result.aggregations["category"]

    def test_translate_highlight(self, translator: PostgresQueryTranslator) -> None:
        """Verify highlight returns ts_headline config."""
        result = translator.translate_highlight(["title", "description"])
        assert result["use_ts_headline"] is True
        assert "title" in result["fields"]
        assert "description" in result["fields"]


class TestElasticsearchQueryTranslator:
    """Tests for ElasticsearchQueryTranslator."""

    @pytest.fixture
    def translator(self) -> ElasticsearchQueryTranslator:
        return ElasticsearchQueryTranslator()

    def test_translate_search_basic(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify basic search translation."""
        result = translator.translate_search("test query")
        assert isinstance(result, TranslatedQuery)
        assert result.query["query"]["multi_match"]["query"] == "test query"
        assert result.query["from"] == 0
        assert result.query["size"] == 20
        assert result.params == []

    def test_translate_search_with_filters_term(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify single-value filter uses term clause."""
        result = translator.translate_search("test", filters={"status": "active"})
        assert "bool" in result.query["query"]
        assert "must" in result.query["query"]["bool"]
        assert "filter" in result.query["query"]["bool"]
        assert result.query["query"]["bool"]["filter"] == [
            {"term": {"status": "active"}},
        ]

    def test_translate_search_with_filters_list(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify list value filter uses terms clause."""
        result = translator.translate_search("test", filters={"status": ["active", "pending"]})
        assert result.query["query"]["bool"]["filter"] == [
            {"terms": {"status": ["active", "pending"]}},
        ]

    def test_translate_search_with_sort(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify sort is included in body."""
        result = translator.translate_search("test", sort=["name:asc"])
        assert result.query["sort"] == ["name:asc"]

    def test_translate_search_pagination(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify pagination parameters."""
        result = translator.translate_search("test", limit=10, offset=5)
        assert result.query["from"] == 5
        assert result.query["size"] == 10

    def test_translate_faceted_search(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify faceted search adds aggregations."""
        result = translator.translate_faceted_search("test", ["category", "price"])
        assert result.aggregations is not None
        assert "category" in result.aggregations
        assert result.aggregations["category"]["terms"]["field"] == "category"
        assert "price" in result.aggregations

    def test_translate_highlight_with_default_tags(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify highlight with default tags."""
        result = translator.translate_highlight(["title"])
        assert result["pre_tags"] == ["<mark>"]
        assert result["post_tags"] == ["</mark>"]
        assert "title" in result["fields"]

    def test_translate_highlight_with_custom_tags(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify highlight with custom tags."""
        result = translator.translate_highlight(
            ["title"],
            pre_tags=["<b>"],
            post_tags=["</b>"],
        )
        assert result["pre_tags"] == ["<b>"]
        assert result["post_tags"] == ["</b>"]

    def test_translate_search_too_many_filter_types(self, translator: ElasticsearchQueryTranslator) -> None:
        """Verify multiple different filters are all included."""
        result = translator.translate_search(
            "test",
            filters={
                "status": "active",
                "tags": ["a", "b"],
            },
        )
        filter_clauses = result.query["query"]["bool"]["filter"]
        assert len(filter_clauses) == 2
