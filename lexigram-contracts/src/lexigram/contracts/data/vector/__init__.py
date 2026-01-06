"""Vector store contracts — protocols, types, and filter primitives.

These define the interface boundary for all vector store backends.
Application code depends on these protocols. Concrete implementations
live in ``lexigram-vector``.

Basic Usage:
    ```python
    from lexigram.contracts.data.vector import (
        VectorStoreProtocol,
        VectorCollectionProtocol,
        VectorRecord,
        SearchQuery,
        Filter,
    )
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.data.vector.enums import (
        DistanceMetric,
        IndexState,
        IndexType,
    )
    from lexigram.contracts.data.vector.exceptions import (
        EmbeddingError,
        VectorError,
        VectorIndexError,
        VectorStoreError,
    )
    from lexigram.contracts.data.vector.filters import (
        Filter,
        FilterOperator,
        LogicalOperator,
        MetadataCondition,
        MetadataConditionGroup,
        MetadataFilter,
    )
    from lexigram.contracts.data.vector.protocols import (
        VectorCollectionProtocol,
        VectorStoreProtocol,
    )
    from lexigram.contracts.data.vector.tenancy import (
        TenantCollectionResolver,
    )
    from lexigram.contracts.data.vector.types import (
        CollectionConfig,
        CollectionInfo,
        DeleteResult,
        SearchQuery,
        UpsertResult,
        VectorRecord,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Exceptions ---
    "VectorError": (
        "lexigram.contracts.data.vector.exceptions",
        "VectorError",
    ),
    "VectorStoreError": (
        "lexigram.contracts.data.vector.exceptions",
        "VectorStoreError",
    ),
    "EmbeddingError": (
        "lexigram.contracts.data.vector.exceptions",
        "EmbeddingError",
    ),
    "VectorIndexError": (
        "lexigram.contracts.data.vector.exceptions",
        "VectorIndexError",
    ),
    # --- Protocols ---
    "VectorStoreProtocol": (
        "lexigram.contracts.data.vector.protocols",
        "VectorStoreProtocol",
    ),
    "VectorCollectionProtocol": (
        "lexigram.contracts.data.vector.protocols",
        "VectorCollectionProtocol",
    ),
    # --- Types ---
    "VectorRecord": (
        "lexigram.contracts.data.vector.types",
        "VectorRecord",
    ),
    "SearchQuery": (
        "lexigram.contracts.data.vector.types",
        "SearchQuery",
    ),
    "SearchResult": (
        "lexigram.contracts.data.vector.types",
        "SearchResult",
    ),
    "CollectionConfig": (
        "lexigram.contracts.data.vector.types",
        "CollectionConfig",
    ),
    "CollectionInfo": (
        "lexigram.contracts.data.vector.types",
        "CollectionInfo",
    ),
    "UpsertResult": (
        "lexigram.contracts.data.vector.types",
        "UpsertResult",
    ),
    "DeleteResult": (
        "lexigram.contracts.data.vector.types",
        "DeleteResult",
    ),
    # --- Tenancy ---
    "TenantCollectionResolver": (
        "lexigram.contracts.data.vector.tenancy",
        "TenantCollectionResolver",
    ),
    # --- Enums ---
    "DistanceMetric": (
        "lexigram.contracts.data.vector.enums",
        "DistanceMetric",
    ),
    "IndexType": (
        "lexigram.contracts.data.vector.enums",
        "IndexType",
    ),
    "IndexState": (
        "lexigram.contracts.data.vector.enums",
        "IndexState",
    ),
    # --- Filters ---
    "Filter": (
        "lexigram.contracts.data.vector.filters",
        "Filter",
    ),
    "MetadataFilter": (
        "lexigram.contracts.data.vector.filters",
        "MetadataFilter",
    ),
    "MetadataCondition": (
        "lexigram.contracts.data.vector.filters",
        "MetadataCondition",
    ),
    "MetadataConditionGroup": (
        "lexigram.contracts.data.vector.filters",
        "MetadataConditionGroup",
    ),
    "FilterOperator": (
        "lexigram.contracts.data.vector.filters",
        "FilterOperator",
    ),
    "LogicalOperator": (
        "lexigram.contracts.data.vector.filters",
        "LogicalOperator",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "CollectionConfig",
    "CollectionInfo",
    "DeleteResult",
    "DistanceMetric",
    "EmbeddingError",
    "Filter",
    "FilterOperator",
    "IndexState",
    "IndexType",
    "LogicalOperator",
    "MetadataCondition",
    "MetadataConditionGroup",
    "MetadataFilter",
    "SearchQuery",
    "SearchResult",
    "TenantCollectionResolver",
    "UpsertResult",
    "VectorCollectionProtocol",
    "VectorError",
    "VectorIndexError",
    "VectorRecord",
    "VectorStoreError",
    "VectorStoreProtocol",
]
