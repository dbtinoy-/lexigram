from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from lexigram.domain import DomainModel
from lexigram.validation import Field


class TransformationStrategy(StrEnum):
    """Available query transformation strategies."""

    EXPANSION = "expansion"
    MULTI_QUERY = "multi_query"
    HYDE = "hyde"
    REWRITE = "rewrite"
    CUSTOM = "custom"


@dataclass
class TransformedQuery:
    """Result of query transformation."""

    original: str
    transformed: list[str]
    strategy: TransformationStrategy
    metadata: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.transformed)

    def __iter__(self) -> Any:
        return iter(self.transformed)


class AbstractQueryTransformer(ABC):
    """Abstract base class for query transformers."""

    @abstractmethod
    async def transform(self, query: str) -> TransformedQuery:
        """Transform a query."""

    @property
    @abstractmethod
    def strategy(self) -> TransformationStrategy:
        """Get the transformation strategy."""


@dataclass(init=False)
class TransformationConfig(DomainModel):
    """Configuration for query transformation pipeline."""

    strategies: list[TransformationStrategy] = Field(
        default_factory=lambda: [TransformationStrategy.EXPANSION],
        description="Transformation strategies to apply",
    )
    combine_results: bool = Field(
        default=True,
        description="Combine results from all strategies",
    )
    max_total_queries: int = Field(
        default=10,
        ge=1,
        description="Maximum total queries to generate",
    )
