from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from lexigram.contracts.security.stores import AsyncSecretStoreProtocol
from lexigram.security.secrets.store import SecretValue


@runtime_checkable
class RotatableSecretStoreProtocol(AsyncSecretStoreProtocol, Protocol):
    """An ``AsyncSecretStoreProtocol`` that also supports credential rotation
    and versioned history."""

    async def rotate(self, key: str) -> VersionedSecret:
        """Generate a new value for *key*, store it as the next version,
        and return the resulting ``VersionedSecret``."""
        ...

    async def get_version(self, key: str, version: int) -> str | None:
        """Return the value of a specific *version*, or ``None`` if absent."""
        ...

    async def list_versions(self, key: str) -> list[SecretVersion]:
        """Return metadata for every known version of *key*, newest first."""
        ...

    async def get_current_version(self, key: str) -> VersionedSecret:
        """Return the full ``VersionedSecret`` for the current (latest) version.
        Raises ``KeyError`` if *key* does not exist."""
        ...


@dataclass(frozen=True)
class SecretVersion:
    """Lightweight metadata for a single version of a secret."""

    version: int
    created_at: datetime


@dataclass(frozen=True)
class VersionedSecret:
    """A secret value together with its version metadata."""

    key: str
    version: int
    value: SecretValue
    created_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)
