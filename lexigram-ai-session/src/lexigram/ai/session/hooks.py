"""Root hook payload surface for lexigram-ai-session."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SessionCheckpointCreatedHook",
    "SessionClosedHook",
    "SessionStartedHook",
]


@dataclass(frozen=True, kw_only=True)
class SessionStartedHook:
    """Payload fired when a session manager opens a new session."""

    session_id: str


@dataclass(frozen=True, kw_only=True)
class SessionCheckpointCreatedHook:
    """Payload fired when checkpointing persists a session snapshot."""

    session_id: str


@dataclass(frozen=True, kw_only=True)
class SessionClosedHook:
    """Payload fired when a session is closed for further writes."""

    session_id: str
