from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.domain import DomainModel


@dataclass(init=False)
class SearchableModel(DomainModel):
    """Base class for models that can be searched."""

    def to_searchable_array(self) -> dict[str, Any]:
        """Convert model to searchable data."""
        return self.model_dump()

    @classmethod
    def get_searchable_key(cls) -> str:
        """Get the searchable key (index name) for this model."""
        return cls.__name__.lower()

    @classmethod
    def get_searchable_settings(cls) -> dict[str, Any]:
        """Get search settings for this model (defaults)."""
        return {
            "searchableAttributes": ["*"],
            "filterableAttributes": [],
            "sortableAttributes": [],
        }
