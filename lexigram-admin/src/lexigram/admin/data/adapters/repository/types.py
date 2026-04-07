"""Type definitions for repository data source."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class AuditEntry:
    """Audit log entry for repository operations."""

    action: str
    entity_type: str
    entity_id: Any
    changes: dict[str, Any] | None = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    user_id: Any = None
