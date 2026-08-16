"""GraphQL schema diffing utilities.

This module provides schema comparison and diffing capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaDiff:
    """Result of schema diff.

    Attributes:
        added: Set of added types/fields.
        removed: Set of removed types/fields.
        changed: Set of changed types/fields.
        breaking: Whether there are breaking changes.
    """

    added: set[str] = field(default_factory=set)
    removed: set[str] = field(default_factory=set)
    changed: set[str] = field(default_factory=set)
    breaking: bool = False

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.removed or self.changed)


class SchemaDiffer:
    """Compare two GraphQL schemas.

    Example:
        differ = SchemaDiffer()
        diff = differ.diff(old_schema, new_schema)

        if diff.breaking:
            # Handle breaking changes
    """

    def diff(self, old_schema: Any, new_schema: Any) -> SchemaDiff:
        """Compare two schemas.

        Args:
            old_schema: Original schema.
            new_schema: New schema.

        Returns:
            SchemaDiff with changes.
        """
        diff = SchemaDiff()

        # This is a simplified implementation
        # Full implementation would compare types, fields, arguments, etc.

        # Get types from both schemas
        old_types = self._get_types(old_schema)
        new_types = self._get_types(new_schema)

        # Find added types
        diff.removed = old_types - new_types

        # Find removed types
        diff.added = new_types - old_types

        # Check for breaking changes
        if diff.removed:
            diff.breaking = True

        return diff

    def _get_types(self, schema: Any) -> set[str]:
        """Get type names from schema."""
        types = set()

        if hasattr(schema, "types"):
            for type_obj in schema.types:
                if hasattr(type_obj, "name"):
                    types.add(type_obj.name)

        return types


__all__ = [
    "SchemaDiff",
    "SchemaDiffer",
]
