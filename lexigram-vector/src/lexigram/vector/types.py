"""Internal type definitions for lexigram-vector."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.domain.models.base import DomainModel
from lexigram.validation import Field


@dataclass
class CollectionState:
    """Mutable internal state of a collection (not exposed in contracts)."""

    name: str
    dimension: int
    distance_metric: str
    index_type: str
    vector_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchProgress:
    """Progress of a batched operation."""

    total: int
    completed: int
    failed: int
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Fraction of successful operations."""
        if self.total == 0:
            return 1.0
        return self.completed / self.total


@dataclass(init=False)
class Embedding(DomainModel):
    """An embedding vector."""

    vector: list[float] = Field(description="Embedding vector")
    model: str = Field(description="Model used to generate embedding")
    dimension: int = Field(description="Vector dimension")
