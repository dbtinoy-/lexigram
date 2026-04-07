"""Root types for lexigram-ai-session."""

from __future__ import annotations

from typing import Any, TypeAlias

# Type aliases for session management
SessionId: TypeAlias = str
TurnId: TypeAlias = str
Metadata: TypeAlias = dict[str, Any]

__all__ = [
    "Metadata",
    "SessionId",
    "TurnId",
]
