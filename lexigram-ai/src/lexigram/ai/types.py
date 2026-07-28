"""Shared type definitions for Lexigram AI.

This module contains type definitions that are used across multiple
sub-modules in intelligence package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.ai.types import EmbeddingModel, ModelProvider, VectorProvider
from lexigram.contracts.core import JSON, Metadata
from lexigram.domain import DomainModel
from lexigram.validation import ConfigDict, Field


# Note: model_serializer not yet implemented in lexigram.contracts
# Using a stub for now
def model_serializer(mode) -> Any:
    def decorator(func) -> Any:
        return func

    return decorator


@dataclass(init=False)
class AIBaseEvent(DomainModel):
    """Base class for AI intelligence domain events."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Metadata = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_serializer(mode="wrap")
    def serialize_model(self, handler) -> Any:
        """Custom serializer to handle datetime objects."""
        data = handler(self)
        # Convert datetime objects to ISO format strings
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data


__all__ = [
    "JSON",
    "AIBaseEvent",
    "EmbeddingModel",
    "Metadata",
    "ModelProvider",
    "VectorProvider",
]
