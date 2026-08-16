"""Root types for lexigram-nosql graph sub-namespace."""

from __future__ import annotations

from typing import Any, TypeAlias

# Type aliases for graph entities
NodeId: TypeAlias = str | int
EdgeId: TypeAlias = str | int
Properties: TypeAlias = dict[str, Any]

__all__ = [
    "EdgeId",
    "NodeId",
    "Properties",
]
