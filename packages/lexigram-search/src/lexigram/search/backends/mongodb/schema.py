"""MongoDB schema management for text search."""

from __future__ import annotations


class MongoSchemaManager:
    """Manages MongoDB search schema creation and migrations."""

    def __init__(self, default_language: str = "english"):
        self.default_language = default_language

    def get_create_text_index_definition(
        self,
        index_name: str,
        weights: dict[str, int] | None = None,
    ) -> dict:
        """Generate the text index definition.

        Args:
            index_name: The collection name
            weights: Field weights for text search relevance
        """
        if weights is None:
            weights = {
                "title": 10,
                "name": 5,
                "description": 3,
                "content": 1,
                "text": 1,
                "body": 1,
            }

        # Build the index fields
        index_fields = {}
        for field in weights.keys():
            index_fields[field] = "text"

        return {
            "name": f"fts_{index_name}",
            "default_language": self.default_language,
            "weights": weights,
            "language_override": "language",
            "textIndexVersion": 3,
        }

    def get_create_text_index_command(
        self, index_name: str, weights: dict[str, int] | None = None
    ) -> list[dict]:
        """Get the createIndex command as a list of documents for the aggregation pipeline."""
        self.get_create_text_index_definition(index_name, weights)

        # For use in aggregation pipeline
        return [
            {"$listIndexes": index_name},
            # This would be executed separately via create_index
        ]

    def get_document_structure(self) -> dict:
        """Get the standard document structure for search collections."""
        return {
            "_id": "string or ObjectId",
            "document": "original document",
            "_searchable": "concatenated searchable text",
            "created_at": "ISODate",
            "updated_at": "ISODate",
        }

    def get_atlas_search_definition(self, index_name: str) -> dict:
        """Get Atlas Search index definition for advanced features."""
        return {
            "mappings": {
                "dynamic": False,
                "fields": {
                    "_searchable": {
                        "type": "string",
                        "analyzer": "standard",
                    },
                    "title": {
                        "type": "string",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256,
                            },
                        },
                    },
                    "name": {
                        "type": "string",
                        "analyzer": "standard",
                    },
                    "description": {
                        "type": "string",
                        "analyzer": "standard",
                    },
                    "content": {
                        "type": "string",
                        "analyzer": "standard",
                    },
                },
            },
            "analyzers": [
                {
                    "name": "custom_analyzer",
                    "charFilters": [],
                    "tokenizer": "standard",
                    "tokenFilters": ["lowercase", "asciifolding"],
                },
            ],
        }

    def get_text_search_pipeline(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Build the text search aggregation pipeline."""
        return [
            {
                "$match": {
                    "$text": {"$search": query},
                },
            },
            {
                "$addFields": {
                    "score": {"$meta": "textScore"},
                },
            },
            {
                "$sort": {"score": -1},
            },
            {"$skip": offset},
            {"$limit": limit},
            {
                "$project": {
                    "document": 1,
                    "score": {"$meta": "textScore"},
                    "_id": 1,
                },
            },
        ]

    def get_faceted_search_pipeline(
        self,
        query: str,
        facets: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Build the faceted search aggregation pipeline."""
        facet_stage = {}
        for facet in facets:
            facet_stage[facet] = {
                "$bucket": {
                    "groupBy": f"$document.{facet}",
                    "output": {"count": {"$sum": 1}},
                },
            }

        return [
            {
                "$match": {
                    "$text": {"$search": query},
                },
            },
            {
                "$addFields": {
                    "score": {"$meta": "textScore"},
                },
            },
            {"$sort": {"score": -1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$facet": {
                    "results": [
                        {"$project": {"document": 1, "score": 1, "_id": 1}},
                    ],
                    "facets": [facet_stage],
                },
            },
        ]


__all__ = ["MongoSchemaManager"]
