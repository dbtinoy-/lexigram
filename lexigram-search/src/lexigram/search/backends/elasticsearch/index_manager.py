"""Elasticsearch index manager for lifecycle management."""

from __future__ import annotations

from typing import Any


class ElasticsearchIndexManager:
    """Manages Elasticsearch index lifecycle, mappings, and aliases."""

    def __init__(
        self,
        index_prefix: str = "lexigram_search_",
        number_of_shards: int = 1,
        number_of_replicas: int = 0,
    ):
        self.index_prefix = index_prefix
        self.number_of_shards = number_of_shards
        self.number_of_replicas = number_of_replicas

    def get_index_name(self, index: str) -> str:
        """Get the full index name with prefix."""
        return f"{self.index_prefix}{index}"

    def get_create_index_settings(self) -> dict:
        """Get the standard index settings."""
        return {
            "number_of_shards": self.number_of_shards,
            "number_of_replicas": self.number_of_replicas,
            "refresh_interval": "1s",
            "max_result_window": 10000,
        }

    def get_create_index_mappings(self) -> dict:
        """Get the standard index mappings."""
        return {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256,
                        },
                        "suggest": {
                            "type": "completion",
                            "contexts": [],
                        },
                    },
                },
                "name": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "description": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "content": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "text": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "body": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "tags": {
                    "type": "keyword",
                },
                "category": {
                    "type": "keyword",
                },
                "created_at": {
                    "type": "date",
                },
                "updated_at": {
                    "type": "date",
                },
            },
        }

    def get_alias_settings(self, index: str) -> dict:
        """Get settings for creating an alias."""
        return {
            "aliases": {
                f"{self.index_prefix}{index}_alias": {},
            },
        }

    async def create_index(self, client: Any, index: str) -> dict:
        """Create an index with mappings and settings."""
        full_name = self.get_index_name(index)

        return await client.indices.create(
            index=full_name,
            mappings=self.get_create_index_mappings(),
            settings=self.get_create_index_settings(),
        )

    async def delete_index(self, client: Any, index: str) -> dict:
        """Delete an index."""
        full_name = self.get_index_name(index)

        return await client.indices.delete(index=full_name)

    async def index_exists(self, client: Any, index: str) -> bool:
        """Check if an index exists."""
        full_name = self.get_index_name(index)

        return await client.indices.exists(index=full_name)

    async def get_index_stats(self, client: Any, index: str) -> dict:
        """Get index statistics."""
        full_name = self.get_index_name(index)

        return await client.indices.stats(index=full_name)

    async def refresh_index(self, client: Any, index: str) -> dict:
        """Refresh an index to make all operations searchable."""
        full_name = self.get_index_name(index)

        return await client.indices.refresh(index=full_name)

    async def forcemerge_index(
        self, client: Any, index: str, max_num_segments: int = 1
    ) -> dict:
        """Force merge an index to optimize for search."""
        full_name = self.get_index_name(index)

        return await client.indices.forcemerge(
            index=full_name,
            max_num_segments=max_num_segments,
        )


__all__ = ["ElasticsearchIndexManager"]
