"""AggregationPipeline insertion-gate tests (Task 3.5 / 4.4)."""

from __future__ import annotations

import pytest

from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.query.pipeline import AggregationPipeline


class TestMatchGuard:
    """match validates the filter at insertion."""

    def test_match_where_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            AggregationPipeline().match({"$where": "return true"})

    def test_match_expr_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            AggregationPipeline().match({"$expr": {"$eq": ["$a", 1]}})

    def test_match_ne_nested_passes_insertion(self) -> None:
        pipeline = AggregationPipeline().match({"password": {"$ne": ""}}).build()
        assert pipeline == [{"$match": {"password": {"$ne": ""}}}]

    def test_match_safe_passes_insertion(self) -> None:
        pipeline = AggregationPipeline().match({"status": "active"}).build()
        assert pipeline == [{"$match": {"status": "active"}}]

    def test_match_does_not_mutate_on_rejection(self) -> None:
        pipeline = AggregationPipeline().match({"status": "active"})
        with pytest.raises(NoSQLFilterError):
            pipeline.match({"$where": "..."})
        assert pipeline.build() == [{"$match": {"status": "active"}}]


class TestLookupGuard:
    """lookup scopes from_collection to a bare collection name."""

    def test_lookup_dotted_name_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            AggregationPipeline().lookup("users.db", "id", "uid", "user")

    def test_lookup_dollar_name_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            AggregationPipeline().lookup("$users", "id", "uid", "user")

    def test_lookup_whitespace_name_rejected(self) -> None:
        with pytest.raises(NoSQLFilterError):
            AggregationPipeline().lookup("users db", "id", "uid", "user")

    def test_lookup_valid_name_passes(self) -> None:
        pipeline = (
            AggregationPipeline()
            .lookup("users", "user_id", "_id", "user_info")
            .build()
        )
        assert pipeline == [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user_info",
                },
            },
        ]


class TestExistingShapesUnchanged:
    """Existing pipeline shapes build unchanged."""

    def test_group_sort_limit_project_unwind(self) -> None:
        pipeline = (
            AggregationPipeline()
            .match({"status": "active"})
            .group("$department", count={"$sum": 1})
            .sort("count", descending=True)
            .limit(10)
            .project(department="$_id", count=1)
            .unwind("$tags")
            .build()
        )
        assert pipeline[0] == {"$match": {"status": "active"}}
        assert pipeline[1]["$group"]["_id"] == "$department"
        assert pipeline[2] == {"$sort": {"count": -1}}
        assert pipeline[3] == {"$limit": 10}
        assert "$project" in pipeline[4]
        assert pipeline[5] == {"$unwind": "$tags"}