"""API Key model for Lexigram Auth."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class APIKey:
    """API Key data model.

    Used for service-to-service authentication.
    """

    key_id: str
    name: str
    key_hash: str
    prefix: str
    user_id: str
    scopes: list[str] = field(default_factory=list)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_active(self) -> bool:
        """Check if the key is active and not expired or revoked."""
        if self.revoked_at is not None:
            return False
        return not (self.expires_at is not None and self.expires_at < datetime.now())


__all__ = [
    "APIKey",
]
