from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class RAGCacheStats(DomainModel):
    """Statistics for cache operations."""

    hits: int = Field(default=0, description="Cache hits")
    misses: int = Field(default=0, description="Cache misses")
    sets: int = Field(default=0, description="Cache sets")
    deletes: int = Field(default=0, description="Cache deletes")
    errors: int = Field(default=0, description="Cache errors")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_operations(self) -> int:
        """Calculate total cache operations."""
        return self.hits + self.misses + self.sets + self.deletes
