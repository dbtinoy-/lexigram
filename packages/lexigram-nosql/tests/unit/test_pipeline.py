"""Tests for AggregationPipeline."""

from __future__ import annotations

from lexigram.nosql.query.pipeline import AggregationPipeline


class TestAggregationPipeline:
    """Tests for the fluent aggregation pipeline builder."""

    def test_empty_pipeline(self) -> None:
        pipeline = AggregationPipeline().build()
        assert pipeline == []

    def test_match(self) -> None:
        pipeline = AggregationPipeline().match({"status": "active"}).build()
        assert pipeline == [{"$match": {"status": "active"}}]

    def test_group_with_accumulators(self) -> None:
        pipeline = (
            AggregationPipeline()
            .group("$department", count={"$sum": 1})
            .build()
        )
        assert pipeline == [
            {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        ]

    def test_project(self) -> None:
        pipeline = (
            AggregationPipeline()
            .project(name=1, email=1, _id=0)
            .build()
        )
        assert pipeline == [{"$project": {"name": 1, "email": 1, "_id": 0}}]

    def test_sort_ascending(self) -> None:
        pipeline = AggregationPipeline().sort("name").build()
        assert pipeline == [{"$sort": {"name": 1}}]

    def test_sort_descending(self) -> None:
        pipeline = AggregationPipeline().sort("count", descending=True).build()
        assert pipeline == [{"$sort": {"count": -1}}]

    def test_limit(self) -> None:
        pipeline = AggregationPipeline().limit(10).build()
        assert pipeline == [{"$limit": 10}]

    def test_skip(self) -> None:
        pipeline = AggregationPipeline().skip(20).build()
        assert pipeline == [{"$skip": 20}]

    def test_unwind_simple(self) -> None:
        pipeline = AggregationPipeline().unwind("$tags").build()
        assert pipeline == [{"$unwind": "$tags"}]

    def test_unwind_preserve_null(self) -> None:
        pipeline = (
            AggregationPipeline()
            .unwind("$tags", preserve_null=True)
            .build()
        )
        assert pipeline == [
            {"$unwind": {"path": "$tags", "preserveNullAndEmptyArrays": True}},
        ]

    def test_lookup(self) -> None:
        pipeline = (
            AggregationPipeline()
            .lookup("orders", "user_id", "_id", "user_orders")
            .build()
        )
        assert pipeline == [{
            "$lookup": {
                "from": "orders",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_orders",
            },
        }]

    def test_add_fields(self) -> None:
        pipeline = (
            AggregationPipeline()
            .add_fields(total={"$sum": "$items.price"})
            .build()
        )
        assert pipeline == [
            {"$addFields": {"total": {"$sum": "$items.price"}}},
        ]

    def test_count(self) -> None:
        pipeline = AggregationPipeline().count("total").build()
        assert pipeline == [{"$count": "total"}]

    def test_facet(self) -> None:
        pipeline = (
            AggregationPipeline()
            .facet(
                by_status=[{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
                total=[{"$count": "count"}],
            )
            .build()
        )
        assert pipeline == [{
            "$facet": {
                "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
                "total": [{"$count": "count"}],
            },
        }]

    def test_complex_pipeline(self) -> None:
        pipeline = (
            AggregationPipeline()
            .match({"status": "active"})
            .group("$department", count={"$sum": 1}, avg_salary={"$avg": "$salary"})
            .sort("count", descending=True)
            .limit(10)
            .project(department="$_id", count=1, avg_salary=1)
            .build()
        )
        assert len(pipeline) == 5
        assert pipeline[0] == {"$match": {"status": "active"}}
        assert pipeline[1]["$group"]["_id"] == "$department"
        assert pipeline[2] == {"$sort": {"count": -1}}
        assert pipeline[3] == {"$limit": 10}
        assert "$project" in pipeline[4]
