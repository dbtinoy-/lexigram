"""Tests for NoSQL types and type aliases."""

from __future__ import annotations

import pytest

from lexigram.nosql.types import (
    DocumentDict,
    FilterDict,
    Pipeline,
    PipelineStage,
    ProjectionDict,
    SortSpec,
    UpdateDict,
)


class TestTypeAliases:
    """Test type alias definitions."""

    def test_document_dict_is_dict(self) -> None:
        """DocumentDict is a dict with string keys and Any values."""
        doc: DocumentDict = {"_id": "123", "name": "test", "count": 42}
        assert doc["_id"] == "123"
        assert doc["name"] == "test"
        assert doc["count"] == 42

    def test_filter_dict_is_dict(self) -> None:
        """FilterDict is a dict for filtering queries."""
        filter_doc: FilterDict = {"status": "active", "age": {"$gte": 18}}
        assert filter_doc["status"] == "active"
        assert filter_doc["age"]["$gte"] == 18

    def test_update_dict_is_dict(self) -> None:
        """UpdateDict is a dict for update operations."""
        update_doc: UpdateDict = {"$set": {"name": "new"}, "$inc": {"count": 1}}
        assert "$set" in update_doc
        assert "$inc" in update_doc

    def test_projection_dict_is_dict(self) -> None:
        """ProjectionDict is a dict for field projection."""
        projection: ProjectionDict = {"_id": 0, "name": 1, "email": 0}
        assert projection["_id"] == 0
        assert projection["name"] == 1

    def test_sort_spec_is_list_of_tuples(self) -> None:
        """SortSpec is a list of (field, direction) tuples."""
        sort: SortSpec = [("created_at", -1), ("name", 1)]
        assert len(sort) == 2
        assert sort[0] == ("created_at", -1)
        assert sort[1] == ("name", 1)

    def test_pipeline_stage_is_dict(self) -> None:
        """PipelineStage is a dict for aggregation stages."""
        stage: PipelineStage = {"$match": {"status": "active"}}
        assert "$match" in stage
        assert stage["$match"]["status"] == "active"

    def test_pipeline_is_list_of_stages(self) -> None:
        """Pipeline is a list of PipelineStage dicts."""
        pipeline: Pipeline = [
            {"$match": {"status": "active"}},
            {"$sort": {"created_at": -1}},
            {"$limit": 10},
        ]
        assert len(pipeline) == 3
        assert "$match" in pipeline[0]
        assert "$sort" in pipeline[1]
        assert "$limit" in pipeline[2]


class TestTypeUsage:
    """Test types can be used in realistic scenarios."""

    def test_document_with_nested_filter(self) -> None:
        """Types work together for realistic NoSQL operations."""
        doc: DocumentDict = {
            "_id": "abc123",
            "user": {"name": "Alice", "email": "alice@example.com"},
            "tags": ["python", "testing"],
        }

        filter_doc: FilterDict = {
            "user.name": "Alice",
            "tags": {"$in": ["python"]},
        }

        update_doc: UpdateDict = {"$set": {"updated": True}, "$push": {"tags": "new"}}

        projection_doc: ProjectionDict = {"_id": 0, "user": 1, "tags": 1}

        sort_spec: SortSpec = [("user.name", 1)]

        assert doc["_id"] == "abc123"
        assert filter_doc["user.name"] == "Alice"
        assert "$set" in update_doc
        assert projection_doc["user"] == 1
        assert sort_spec[0][0] == "user.name"

    def test_pipeline_aggregation_workflow(self) -> None:
        """Pipeline types work for aggregation workflows."""
        pipeline: Pipeline = [
            {"$match": {"status": {"$ne": "deleted"}}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
            {"$project": {"_id": 0, "category": "$_id", "count": 1}},
        ]

        assert len(pipeline) == 5
        assert "$match" in pipeline[0]
        assert "$group" in pipeline[1]
        assert "$sort" in pipeline[2]
        assert "$limit" in pipeline[3]
        assert "$project" in pipeline[4]