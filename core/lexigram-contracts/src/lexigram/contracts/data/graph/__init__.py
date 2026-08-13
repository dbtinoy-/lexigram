"""Graph store contracts — protocols, types, and filter primitives."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.data.graph.enums import (
        ConstraintKind,
        EdgeDirection,
        IndexKind,
        MergeAction,
        ReturnType,
    )
    from lexigram.contracts.data.graph.filters import (
        Prop,
        PropertyCondition,
        PropertyConditionGroup,
        PropertyFilter,
        PropertyOperator,
    )
    from lexigram.contracts.data.graph.protocols import (
        GraphProtocol,
        GraphStoreProtocol,
    )
    from lexigram.contracts.data.graph.tenancy import (
        GraphTenancyStrategy,
    )
    from lexigram.contracts.data.graph.types import (
        BulkEdgeResult,
        BulkNodeResult,
        ConstraintSpec,
        EdgeResult,
        EdgeSpec,
        GraphEdge,
        GraphInfo,
        GraphNode,
        GraphPath,
        IndexSpec,
        NodeResult,
        NodeSpec,
        StartSpec,
        TraversalQuery,
        TraversalStep,
    )
    from lexigram.contracts.data.types import LogicalOperator

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Protocols ---
    "GraphStoreProtocol": (
        "lexigram.contracts.data.graph.protocols",
        "GraphStoreProtocol",
    ),
    "GraphProtocol": (
        "lexigram.contracts.data.graph.protocols",
        "GraphProtocol",
    ),
    # --- Types ---
    "GraphNode": ("lexigram.contracts.data.graph.types", "GraphNode"),
    "GraphEdge": ("lexigram.contracts.data.graph.types", "GraphEdge"),
    "GraphPath": ("lexigram.contracts.data.graph.types", "GraphPath"),
    "NodeSpec": ("lexigram.contracts.data.graph.types", "NodeSpec"),
    "EdgeSpec": ("lexigram.contracts.data.graph.types", "EdgeSpec"),
    "NodeResult": ("lexigram.contracts.data.graph.types", "NodeResult"),
    "EdgeResult": ("lexigram.contracts.data.graph.types", "EdgeResult"),
    "BulkNodeResult": ("lexigram.contracts.data.graph.types", "BulkNodeResult"),
    "BulkEdgeResult": ("lexigram.contracts.data.graph.types", "BulkEdgeResult"),
    "GraphInfo": ("lexigram.contracts.data.graph.types", "GraphInfo"),
    "StartSpec": ("lexigram.contracts.data.graph.types", "StartSpec"),
    "TraversalStep": ("lexigram.contracts.data.graph.types", "TraversalStep"),
    "TraversalQuery": ("lexigram.contracts.data.graph.types", "TraversalQuery"),
    "IndexSpec": ("lexigram.contracts.data.graph.types", "IndexSpec"),
    "ConstraintSpec": ("lexigram.contracts.data.graph.types", "ConstraintSpec"),
    # --- Enums ---
    "EdgeDirection": ("lexigram.contracts.data.graph.enums", "EdgeDirection"),
    "ReturnType": ("lexigram.contracts.data.graph.enums", "ReturnType"),
    "IndexKind": ("lexigram.contracts.data.graph.enums", "IndexKind"),
    "ConstraintKind": ("lexigram.contracts.data.graph.enums", "ConstraintKind"),
    "MergeAction": ("lexigram.contracts.data.graph.enums", "MergeAction"),
    # --- Tenancy ---
    "GraphTenancyStrategy": (
        "lexigram.contracts.data.graph.tenancy",
        "GraphTenancyStrategy",
    ),
    # --- Filters ---
    "Prop": ("lexigram.contracts.data.graph.filters", "Prop"),
    "PropertyFilter": ("lexigram.contracts.data.graph.filters", "PropertyFilter"),
    "PropertyCondition": ("lexigram.contracts.data.graph.filters", "PropertyCondition"),
    "PropertyConditionGroup": (
        "lexigram.contracts.data.graph.filters",
        "PropertyConditionGroup",
    ),
    "PropertyOperator": ("lexigram.contracts.data.graph.filters", "PropertyOperator"),
    "LogicalOperator": ("lexigram.contracts.data.types", "LogicalOperator"),
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
    "BulkEdgeResult",
    "BulkNodeResult",
    "ConstraintKind",
    "ConstraintSpec",
    "EdgeDirection",
    "EdgeResult",
    "EdgeSpec",
    "GraphEdge",
    "GraphInfo",
    "GraphNode",
    "GraphPath",
    "GraphProtocol",
    "GraphStoreProtocol",
    "GraphTenancyStrategy",
    "IndexKind",
    "IndexSpec",
    "LogicalOperator",
    "MergeAction",
    "NodeResult",
    "NodeSpec",
    "Prop",
    "PropertyCondition",
    "PropertyConditionGroup",
    "PropertyFilter",
    "PropertyOperator",
    "ReturnType",
    "StartSpec",
    "TraversalQuery",
    "TraversalStep",
]
