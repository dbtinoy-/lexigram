"""Unit tests for canonical filter-dict rendering across backend dialects."""

from __future__ import annotations

import pytest

from lexigram.search.backends.filters import (
    FilterRenderError,
    render_elasticsearch,
    render_filters,
    render_meilisearch,
    render_mongodb,
    render_mysql,
    render_postgres,
    render_sqlite,
    render_typesense,
)

EQ_FILTERS = {"status": "active"}
OR_FILTERS = {"$or": [{"role": "admin"}, {"role": "editor"}]}
NOT_FILTERS = {"$not": {"status": "banned"}}
AND_NESTED = {"$and": [{"a": 1}, {"$or": [{"b": 2}, {"c": 3}]}]}
OPS_FILTERS = {
    "score": {"gte": 80},
    "tags": {"in": ["x", "y"]},
    "title": {"contains": "framework"},
    "state": {"ne": "deleted"},
}


class TestRenderElasticsearch:
    """Elasticsearch / OpenSearch clause rendering."""

    def test_equality_renders_term(self) -> None:
        assert render_elasticsearch(EQ_FILTERS) == [{"term": {"status": "active"}}]

    def test_bare_list_renders_terms(self) -> None:
        assert render_elasticsearch({"tags": ["x", "y"]}) == [
            {"terms": {"tags": ["x", "y"]}}
        ]

    def test_in_renders_terms(self) -> None:
        assert render_elasticsearch({"tags": {"in": ["x", "y"]}}) == [
            {"terms": {"tags": ["x", "y"]}}
        ]

    def test_nin_renders_must_not_terms(self) -> None:
        assert render_elasticsearch({"tags": {"nin": ["x"]}}) == [
            {"bool": {"must_not": [{"terms": {"tags": ["x"]}}]}}
        ]

    def test_ne_renders_must_not_term(self) -> None:
        assert render_elasticsearch({"state": {"ne": "deleted"}}) == [
            {"bool": {"must_not": [{"term": {"state": "deleted"}}]}}
        ]

    def test_comparison_renders_range(self) -> None:
        assert render_elasticsearch({"score": {"gte": 80}}) == [
            {"range": {"score": {"gte": 80}}}
        ]

    def test_multi_comparison_renders_range(self) -> None:
        assert render_elasticsearch({"score": {"gte": 50, "lte": 100}}) == [
            {"range": {"score": {"gte": 50, "lte": 100}}}
        ]

    def test_contains_renders_wildcard(self) -> None:
        assert render_elasticsearch({"title": {"contains": "framework"}}) == [
            {"wildcard": {"title": {"value": "*framework*", "case_insensitive": True}}}
        ]

    def test_or_renders_should(self) -> None:
        assert render_elasticsearch(OR_FILTERS) == [
            {
                "bool": {
                    "should": [
                        {"term": {"role": "admin"}},
                        {"term": {"role": "editor"}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        ]

    def test_not_renders_must_not(self) -> None:
        assert render_elasticsearch(NOT_FILTERS) == [
            {"bool": {"must_not": [{"term": {"status": "banned"}}]}}
        ]

    def test_and_groups_nested_should(self) -> None:
        clauses = render_elasticsearch(AND_NESTED)
        assert clauses == [
            {"term": {"a": 1}},
            {
                "bool": {
                    "should": [{"term": {"b": 2}}, {"term": {"c": 3}}],
                    "minimum_should_match": 1,
                }
            },
        ]

    def test_opensearch_identical(self) -> None:
        from lexigram.search.backends.filters import render_opensearch

        assert render_opensearch(OR_FILTERS) == render_elasticsearch(OR_FILTERS)

    def test_unknown_operator_raises(self) -> None:
        with pytest.raises(FilterRenderError, match="unsupported operator"):
            render_elasticsearch({"a": {"bogus": 1}})

    def test_invalid_field_name_raises(self) -> None:
        with pytest.raises(FilterRenderError, match="invalid field name"):
            render_elasticsearch({"bad field": 1})


class TestRenderMeilisearch:
    """Meilisearch filter-string rendering."""

    def test_equality_quotes_strings(self) -> None:
        assert render_meilisearch(EQ_FILTERS) == 'status = "active"'

    def test_numeric_equality_bare(self) -> None:
        assert render_meilisearch({"score": 80}) == "score = 80"

    def test_in_renders_in_list(self) -> None:
        assert render_meilisearch({"tags": {"in": ["x", "y"]}}) == 'tags IN ["x", "y"]'

    def test_bare_list_renders_in(self) -> None:
        assert render_meilisearch({"tags": ["x", "y"]}) == 'tags IN ["x", "y"]'

    def test_nin_renders_not_in(self) -> None:
        assert render_meilisearch({"tags": {"nin": ["x"]}}) == 'tags NOT IN ["x"]'

    def test_ne_renders_not_equal(self) -> None:
        assert render_meilisearch({"state": {"ne": "deleted"}}) == 'state != "deleted"'

    def test_gte_renders_ge(self) -> None:
        assert render_meilisearch({"score": {"gte": 80}}) == "score >= 80"

    def test_contains_degrades_to_equality(self) -> None:
        assert render_meilisearch({"title": {"contains": "framework"}}) == (
            'title = "framework"'
        )

    def test_or_renders_parenthesized_join(self) -> None:
        assert render_meilisearch(OR_FILTERS) == '(role = "admin") OR (role = "editor")'

    def test_not_renders_not_prefix(self) -> None:
        assert render_meilisearch(NOT_FILTERS) == 'NOT (status = "banned")'

    def test_and_with_nested_or(self) -> None:
        rendered = render_meilisearch(AND_NESTED)
        assert rendered == "(a = 1) AND ((b = 2) OR (c = 3))"

    def test_exists_raises(self) -> None:
        with pytest.raises(FilterRenderError, match="exists"):
            render_meilisearch({"a": {"exists": True}})


class TestRenderTypesense:
    """Typesense filter-string rendering."""

    def test_equality_renders_colon(self) -> None:
        assert render_typesense(EQ_FILTERS) == "status:active"

    def test_in_renders_bracket_list(self) -> None:
        assert render_typesense({"tags": {"in": [1, 2]}}) == "tags:[1,2]"

    def test_nin_renders_negated_bracket_list(self) -> None:
        assert render_typesense({"tags": {"nin": [1]}}) == "!(tags:[1])"

    def test_ne_renders_not_equal(self) -> None:
        assert render_typesense({"state": {"ne": "x"}}) == "state:!=x"

    def test_comparison_renders_operator_prefix(self) -> None:
        assert render_typesense({"score": {"gte": 80}}) == "score:>=80"

    def test_contains_renders_contains_fn(self) -> None:
        assert render_typesense({"title": {"contains": "framework"}}) == (
            "title:contains(framework)"
        )

    def test_or_renders_double_pipe(self) -> None:
        assert render_typesense(OR_FILTERS) == "(role:admin) || (role:editor)"

    def test_not_renders_bang_group(self) -> None:
        assert render_typesense(NOT_FILTERS) == "!(status:banned)"

    def test_and_with_nested_or(self) -> None:
        assert render_typesense(AND_NESTED) == "(a:1) && ((b:2) || (c:3))"

    def test_exists_raises(self) -> None:
        with pytest.raises(FilterRenderError, match="exists"):
            render_typesense({"a": {"exists": True}})


class TestRenderMongoDB:
    """MongoDB query-document rendering."""

    def test_equality_passthrough(self) -> None:
        assert render_mongodb(EQ_FILTERS) == {"status": "active"}

    def test_in_renders_dollar_in(self) -> None:
        assert render_mongodb({"tags": {"in": ["x", "y"]}}) == {
            "tags": {"$in": ["x", "y"]}
        }

    def test_nin_renders_dollar_nin(self) -> None:
        assert render_mongodb({"tags": {"nin": ["x"]}}) == {"tags": {"$nin": ["x"]}}

    def test_ne_renders_dollar_ne(self) -> None:
        assert render_mongodb({"state": {"ne": "x"}}) == {"state": {"$ne": "x"}}

    def test_comparison_renders_dollar_op(self) -> None:
        assert render_mongodb({"score": {"gte": 80}}) == {"score": {"$gte": 80}}

    def test_contains_renders_regex(self) -> None:
        assert render_mongodb({"title": {"contains": "fram.work"}}) == {
            "title": {"$regex": "fram\\.work", "$options": "i"}
        }

    def test_legacy_star_wildcard_preserved(self) -> None:
        assert render_mongodb({"title": "na*me"}) == {
            "title": {"$regex": "na.*me", "$options": "i"}
        }

    def test_or_renders_dollar_or(self) -> None:
        assert render_mongodb(OR_FILTERS) == {
            "$or": [{"role": "admin"}, {"role": "editor"}]
        }

    def test_not_renders_dollar_nor(self) -> None:
        assert render_mongodb(NOT_FILTERS) == {"$nor": [{"status": "banned"}]}

    def test_and_nested(self) -> None:
        rendered = render_mongodb(AND_NESTED)
        assert rendered == {"$and": [{"a": 1}, {"$or": [{"b": 2}, {"c": 3}]}]}


class TestRenderSQL:
    """SQL WHERE rendering for postgres / mysql / sqlite."""

    def test_postgres_equality(self) -> None:
        clause, params = render_postgres(EQ_FILTERS)
        assert clause == "document->>'status' = $1"
        assert params == ["active"]

    def test_postgres_offset_placeholders(self) -> None:
        clause, params = render_postgres({"a": 1, "b": {"gte": 5}}, offset=3)
        assert clause == "document->>'a' = $3 AND document->>'b' >= $4"
        assert params == [1, 5]

    def test_mysql_equality(self) -> None:
        clause, params = render_mysql(EQ_FILTERS)
        assert clause == "JSON_UNQUOTE(JSON_EXTRACT(document, '$.status')) = %s"
        assert params == ["active"]

    def test_sqlite_equality(self) -> None:
        clause, params = render_sqlite(EQ_FILTERS)
        assert clause == "json_extract(document, '$.status') = ?"
        assert params == ["active"]

    def test_in_renders_placeholders(self) -> None:
        clause, params = render_postgres({"tags": {"in": ["x", "y"]}})
        assert clause == "document->>'tags' IN ($1, $2)"
        assert params == ["x", "y"]

    def test_nin_renders_not_in(self) -> None:
        clause, params = render_postgres({"tags": {"nin": ["x"]}})
        assert clause == "document->>'tags' NOT IN ($1)"
        assert params == ["x"]

    def test_ne_renders_not_equal(self) -> None:
        clause, params = render_postgres({"state": {"ne": "x"}})
        assert clause == "document->>'state' <> $1"
        assert params == ["x"]

    def test_comparison_renders_operator(self) -> None:
        clause, params = render_postgres({"score": {"lt": 10}})
        assert clause == "document->>'score' < $1"
        assert params == [10]

    def test_contains_renders_like(self) -> None:
        clause, params = render_sqlite({"title": {"contains": "framework"}})
        assert clause == "json_extract(document, '$.title') LIKE ?"
        assert params == ["%framework%"]

    def test_exists_renders_null_check(self) -> None:
        clause, params = render_postgres({"a": {"exists": True}})
        assert clause == "document->>'a' IS NOT NULL"
        assert params == []

    def test_or_renders_join(self) -> None:
        clause, params = render_postgres(OR_FILTERS)
        assert clause == "(document->>'role' = $1) OR (document->>'role' = $2)"
        assert params == ["admin", "editor"]

    def test_not_renders_not(self) -> None:
        clause, params = render_postgres(NOT_FILTERS)
        assert clause == "NOT (document->>'status' = $1)"
        assert params == ["banned"]

    def test_and_nested(self) -> None:
        clause, params = render_sqlite(AND_NESTED)
        assert (
            clause
            == "(json_extract(document, '$.a') = ?) AND ((json_extract(document, '$.b') = ?) OR (json_extract(document, '$.c') = ?))"
        )
        assert params == [1, 2, 3]


class TestRenderDispatch:
    """Registry-based dispatch and dialect validation."""

    @pytest.mark.parametrize(
        "dialect",
        [
            "elasticsearch",
            "opensearch",
            "meilisearch",
            "typesense",
            "mongodb",
            "memory",
        ],
    )
    def test_dict_dialects_accept_equality(self, dialect: str) -> None:
        result = render_filters(dialect, EQ_FILTERS)
        assert result is not None

    def test_unknown_dialect_raises(self) -> None:
        with pytest.raises(FilterRenderError, match="unknown filter dialect"):
            render_filters("not-a-backend", EQ_FILTERS)

    def test_malformed_dollar_or_raises(self) -> None:
        with pytest.raises(FilterRenderError, match=r"\$or"):
            render_elasticsearch({"$or": {"a": 1}})

    def test_malformed_dollar_not_raises(self) -> None:
        with pytest.raises(FilterRenderError, match=r"\$not"):
            render_elasticsearch({"$not": [{"a": 1}]})
