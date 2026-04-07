"""Core types for the RBAC system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Permission:
    """A single permission string with optional scope."""

    resource: str  # e.g., "users"
    action: str  # e.g., "read", "write", "delete"
    scope: str | None = None  # e.g., "self", "team", "all"

    def __str__(self) -> str:
        if self.scope:
            return f"{self.resource}.{self.action}:{self.scope}"
        return f"{self.resource}.{self.action}"


@dataclass
class Role:
    """A named collection of permissions."""

    name: str
    description: str = ""
    permissions: list[Permission] = field(default_factory=list)
    inherits: list[str] = field(default_factory=list)  # Parent role names


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
