"""Core types for the RBAC system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PolicyContext:
    """Context passed to policy evaluators."""

    user: Any
    resource_name: str
    action: str
    record: Any | None = None  # For record-level/RLS policies


@runtime_checkable
class Policy(Protocol):
    """Protocol for policy evaluators."""

    def __call__(self, context: PolicyContext) -> bool: ...
