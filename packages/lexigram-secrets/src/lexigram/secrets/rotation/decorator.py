from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.secrets.types import (
        RotatableSecretStoreProtocol,
        VersionedSecret,
    )


@dataclass(frozen=True)
class RotationSchedule:
    """Policy for automatic rotation of credentials."""

    max_age_seconds: float
    warning_before_seconds: float = 86400.0
    grace_period_seconds: float = 300.0


_MAX_GRACE_ENTRIES = 64


class RotationDecorator:
    """Wraps a ``RotatableSecretStoreProtocol`` with age-checked automatic rotation.

    On ``get_rotated`` the decorator checks the current version's age against
    ``schedule.max_age_seconds``. If exceeded it calls ``rotate`` on the underlying
    store automatically.

    After rotation the old version is still served via ``get_current_version``
    until the *grace period* (``grace_period_seconds``) elapses.  The
    ``VersionedSecret`` returned after rotation has its ``expires_at`` field
    populated.
    """

    def __init__(
        self,
        store: RotatableSecretStoreProtocol,
        schedule: RotationSchedule,
    ) -> None:
        self._store = store
        self._schedule = schedule
        self._rotated_at: dict[str, datetime] = {}
        self._rotated_old: dict[str, VersionedSecret] = {}

    def _evict_if_expired(self, key: str) -> None:
        rotated_at = self._rotated_at.get(key)
        if rotated_at is not None:
            elapsed = (datetime.now(UTC) - rotated_at).total_seconds()
            if elapsed >= self._schedule.grace_period_seconds:
                self._rotated_at.pop(key, None)
                self._rotated_old.pop(key, None)

    def _evict_oldest(self) -> None:
        while len(self._rotated_old) > _MAX_GRACE_ENTRIES:
            oldest = min(self._rotated_at, key=self._rotated_at.__getitem__)
            self._rotated_at.pop(oldest, None)
            self._rotated_old.pop(oldest, None)

    async def get_rotated(self, key: str) -> tuple[str, bool]:
        """Return ``(value, was_rotated)``.

        If the current version of *key* is older than ``max_age_seconds`` a new
        version is generated first.  The old version is preserved in a grace
        buffer so that callers still see it until the grace period expires.
        """
        self._evict_if_expired(key)
        current = await self._store.get_current_version(key)
        age = (datetime.now(UTC) - current.created_at).total_seconds()
        if age > self._schedule.max_age_seconds:
            self._rotated_old[key] = current
            self._rotated_at[key] = datetime.now(UTC)
            self._evict_oldest()
            new_secret: VersionedSecret = await self._store.rotate(key)
            return str(new_secret.value), True
        return str(current.value), False

    async def get_current_version(self, key: str) -> VersionedSecret:
        """Return the current version, respecting the grace period.

        If *key* was recently rotated and the grace period has not yet elapsed
        the *old* version is returned.  Once the grace period expires the new
        version from the underlying store is served.
        """
        rotated_at = self._rotated_at.get(key)
        if rotated_at is not None:
            self._evict_if_expired(key)
            if self._rotated_at.get(key) is not None:
                return self._rotated_old[key]
        return await self._store.get_current_version(key)

    async def check_warnings(self, key: str) -> str | None:
        """Return a warning message if *key* is approaching its rotation deadline,
        or ``None`` if no warning is needed."""
        current = await self._store.get_current_version(key)
        age = (datetime.now(UTC) - current.created_at).total_seconds()
        warning_threshold = (
            self._schedule.max_age_seconds - self._schedule.warning_before_seconds
        )
        if age >= warning_threshold:
            remaining = self._schedule.max_age_seconds - age
            return (
                f"Secret '{key}' approaching rotation deadline: "
                f"{remaining:.0f}s remaining"
            )
        return None
