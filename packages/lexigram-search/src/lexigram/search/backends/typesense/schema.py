"""Typesense schema management."""

from __future__ import annotations

from typing import Any


class TypesenseSchemaManager:
    """Manages Typesense collection schemas."""

    def get_default_schema(self, name: str) -> dict:
        """Get the default collection schema.

        Args:
            name: The collection name

        Returns:
            Typesense schema configuration
        """
        return {
            "name": name,
            "fields": [
                {"name": "id", "type": "string", "facet": False},
                {"name": "title", "type": "string", "facet": False, "optional": True},
                {"name": "name", "type": "string", "facet": False, "optional": True},
                {
                    "name": "description",
                    "type": "string",
                    "facet": False,
                    "optional": True,
                },
                {"name": "content", "type": "string", "facet": False, "optional": True},
                {"name": "text", "type": "string", "facet": False, "optional": True},
                {"name": "body", "type": "string", "facet": False, "optional": True},
                {"name": "tags", "type": "string[]", "facet": True, "optional": True},
                {"name": "category", "type": "string", "facet": True, "optional": True},
                {"name": "status", "type": "string", "facet": True, "optional": True},
                {
                    "name": "created_at",
                    "type": "int64",
                    "facet": False,
                    "optional": True,
                },
                {
                    "name": "updated_at",
                    "type": "int64",
                    "facet": False,
                    "optional": True,
                },
            ],
            "token_separators": [
                "+",
                "-",
                "@",
                "$",
                "!",
                "^",
                "&",
                "*",
                "(",
                ")",
                "{",
                "}",
                "[",
                "]",
                "|",
                "\\",
                "/",
                "~",
                "`",
                '"',
                "'",
                ":",
                ";",
                ",",
                ".",
            ],
            "fallback_field": "title",
        }

    def get_faceted_schema(self, name: str, facets: list[str]) -> dict:
        """Get a schema with additional facet fields.

        Args:
            name: The collection name
            facets: List of fields to facet on

        Returns:
            Typesense schema with facets
        """
        schema = self.get_default_schema(name)

        # Add custom facet fields
        for facet in facets:
            # Check if field already exists
            existing = [f for f in schema["fields"] if f["name"] == facet]
            if not existing:
                schema["fields"].append(
                    {
                        "name": facet,
                        "type": "string",
                        "facet": True,
                        "optional": True,
                    }
                )

        return schema

    def get_autocomplete_schema(self, name: str) -> dict:
        """Get a schema optimized for autocomplete.

        Args:
            name: The collection name

        Returns:
            Typesense schema optimized for autocomplete
        """
        return {
            "name": name,
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "name", "type": "string"},
            ],
            "token_separators": [
                "+",
                "-",
                "@",
                "$",
                "!",
                "^",
                "&",
                "*",
                "(",
                ")",
                "{",
                "}",
                "[",
                "]",
                "|",
                "\\",
                "/",
            ],
        }

    def get_geo_schema(self, name: str) -> dict:
        """Get a schema with geo search support.

        Args:
            name: The collection name

        Returns:
            Typesense schema with geo field
        """
        schema = self.get_default_schema(name)
        schema["fields"].append(
            {
                "name": "location",
                "type": "geopoint",
                "facet": False,
                "optional": True,
            }
        )

        return schema

    async def create_collection(self, client: Any, name: str) -> dict:
        """Create a collection with default schema."""
        schema = self.get_default_schema(name)

        try:
            result = client.collections.create(schema)
            return {"status": "created", "result": result}
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            return {"status": "error", "error": str(e)}

    async def delete_collection(self, client: Any, name: str) -> dict:
        """Delete a collection."""
        try:
            result = client.collections[name].delete()
            return {"status": "deleted", "result": result}
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            return {"status": "error", "error": str(e)}


__all__ = ["TypesenseSchemaManager"]
