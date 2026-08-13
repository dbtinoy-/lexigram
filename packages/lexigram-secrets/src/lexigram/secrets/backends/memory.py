"""In-memory rotatable secret store backend.

Used when ``backend_type="memory"`` — a process-local store useful for
development and ephemeral environments. Data is not persisted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import secrets

from lexigram.secrets.types import (
    SecretVersion,
    VersionedSecret,
)
from lexigram.security.secrets.store import SecretValue

__all__ = ["InMemoryRotatableSecretStore"]


@dataclass
class _SecretRecord:
    """One in-memory secret with its version history."""

    versions: dict[int, str] = field(default_factory=dict)
    created_at: dict[int, datetime] = field(default_factory=dict)
    next_version: int = 1
    metadata: dict[int, dict[str, object]] = field(default_factory=dict)


class InMemoryRotatableSecretStore:
    """In-memory ``RotatableSecretStoreProtocol`` implementation.

    Generates random hex values on ``rotate``.
    """

    def __init__(self) -> None:
        self._records: dict[str, _SecretRecord] = {}

    async def get(self, name: str) -> str | None:
        record = self._records.get(name)
        if record is None:
            return None
        latest = record.next_version - 1
        return record.versions.get(latest)

    async def get_bulk(self, *names: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in names:
            val = await self.get(name)
            if val is not None:
                result[name] = val
        return result

    async def set(self, name: str, value: str) -> None:
        record = self._records.setdefault(name, _SecretRecord())
        v = record.next_version
        record.versions[v] = value
        record.created_at[v] = datetime.now(UTC)
        record.next_version += 1

    async def delete(self, name: str) -> None:
        self._records.pop(name, None)

    async def rotate(self, key: str) -> VersionedSecret:
        value = SecretValue(secrets.token_hex(32))
        await self.set(key, str(value))
        record = self._records[key]
        v = record.next_version - 1
        return VersionedSecret(
            key=key,
            version=v,
            value=value,
            created_at=record.created_at[v],
        )

    async def get_version(self, key: str, version: int) -> str | None:
        record = self._records.get(key)
        if record is None:
            return None
        return record.versions.get(version)

    async def list_versions(self, key: str) -> list[SecretVersion]:
        record = self._records.get(key)
        if record is None:
            return []
        return [
            SecretVersion(version=v, created_at=record.created_at[v])
            for v in sorted(record.versions, reverse=True)
        ]

    async def get_current_version(self, key: str) -> VersionedSecret:
        record = self._records.get(key)
        if record is None:
            msg = f"Secret '{key}' not found"
            raise KeyError(msg)
        latest = record.next_version - 1
        raw = record.versions[latest]
        return VersionedSecret(
            key=key,
            version=latest,
            value=SecretValue(raw),
            created_at=record.created_at[latest],
            metadata=record.metadata.get(latest, {}),
        )
