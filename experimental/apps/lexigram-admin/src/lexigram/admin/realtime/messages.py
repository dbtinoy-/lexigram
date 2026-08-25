"""WebSocket message value types and serialization for lexigram-admin.

Defines :class:`WSMessageType` and :class:`WSMessage` — the wire format
shared by the admin WebSocket manager, handlers, and notifiers.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


class WSMessageType(StrEnum):
    """WebSocket message types."""

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ACTION = "action"
    PING = "ping"

    # Server -> Client
    EVENT = "event"
    NOTIFICATION = "notification"
    ERROR = "error"
    PONG = "pong"
    ACK = "ack"


@dataclass
class WSMessage:
    """WebSocket message."""

    type: WSMessageType | str
    data: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": str(
                self.type.value if isinstance(self.type, WSMessageType) else self.type,
            ),
            "data": self.data,
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WSMessage:
        """Create from dictionary."""
        msg_type = data.get("type", "")
        with contextlib.suppress(
            ValueError
        ):  # Keep as string if not a valid WSMessageType
            msg_type = WSMessageType(msg_type)

        return cls(
            type=msg_type,
            data=data.get("data", {}),
            id=data.get("id"),
        )
