"""Base abstract classes for vector store drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import TYPE_CHECKING

from lexigram.contracts.data.vector import (
    VectorCollectionProtocol,
    VectorStoreProtocol,
)

if TYPE_CHECKING:
    from lexigram.contracts.data.vector import (
        DistanceMetric,
    )

_COLLECTION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BaseVectorStore(VectorStoreProtocol, ABC):
    """Common logic for all vector store implementations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""


class BaseVectorCollection(VectorCollectionProtocol, ABC):
    """Common logic for all vector collection implementations."""

    def __init__(
        self,
        name: str,
        dimension: int,
        distance_metric: DistanceMetric,
    ):
        if _COLLECTION_NAME_RE.fullmatch(name) is None:
            raise ValueError(
                f"collection name must be a plain SQL identifier, got {name!r}"
            )
        self._name = name
        self._dimension = dimension
        self._distance_metric = distance_metric

    @property
    def name(self) -> str:
        return self._name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def distance_metric(self) -> DistanceMetric:
        return self._distance_metric
