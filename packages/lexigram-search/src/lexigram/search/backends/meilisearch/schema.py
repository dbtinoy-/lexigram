"""MeiliSearch index management and settings."""

from __future__ import annotations

from typing import Any


class MeiliSearchIndexManager:
    """Manages MeiliSearch index creation and settings."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def get_default_settings(self) -> dict:
        """Get the default index settings."""
        return {
            "searchableAttributes": [
                "title",
                "name",
                "description",
                "content",
                "text",
                "body",
            ],
            "displayedAttributes": [
                "id",
                "title",
                "name",
                "description",
                "content",
                "created_at",
                "updated_at",
            ],
            "filterableAttributes": [
                "category",
                "tags",
                "status",
                "type",
            ],
            "sortableAttributes": [
                "created_at",
                "updated_at",
                "title",
            ],
            "rankingRules": [
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
            ],
            "distinctAttribute": "id",
            "typoTolerance": {
                "enabled": True,
                "minWordSizeForTypos": {
                    "oneTypo": 4,
                    "twoTypos": 8,
                },
            },
        }

    def get_autocomplete_settings(self) -> dict:
        """Get settings optimized for autocomplete."""
        return {
            "searchableAttributes": [
                "title",
                "name",
            ],
            "displayedAttributes": [
                "id",
                "title",
                "name",
            ],
            "rankingRules": [
                "exactness",
                "typo",
                "words",
                "attribute",
                "sort",
            ],
            "typoTolerance": {
                "enabled": True,
            },
        }

    def get_faceted_settings(self, facets: list[str]) -> dict:
        """Get settings optimized for faceted search."""
        settings = self.get_default_settings()
        settings["filterableAttributes"] = facets
        return settings

    async def create_index(self, client: Any, index_name: str) -> dict:
        """Create an index with default settings."""
        try:
            # Create index
            client.create_index(index_name, {"primaryKey": "id"})

            # Get the index
            index = client.index(index_name)

            # Update settings
            index.update_settings(self.get_default_settings())

            return {"status": "created", "index": index_name}
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            return {"status": "error", "error": str(e)}

    async def delete_index(self, client: Any, index_name: str) -> dict:
        """Delete an index."""
        try:
            client.delete_index(index_name)
            return {"status": "deleted", "index": index_name}
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            return {"status": "error", "error": str(e)}


__all__ = ["MeiliSearchIndexManager"]
