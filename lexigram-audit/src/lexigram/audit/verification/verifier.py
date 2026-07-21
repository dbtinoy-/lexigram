"""Audit trail tamper detection via HMAC-SHA256 checksum verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.audit.store.sql import entry_to_row
from lexigram.audit.verification.checksum import (
    compute_audit_checksum,
    verify_audit_checksum,
)
from lexigram.contracts.audit import (
    AuditEntry,
    AuditMismatch,
    AuditMismatchReason,
    AuditQuery,
    AuditStoreProtocol,
)
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditVerifier"]

logger = get_logger(__name__)


class AuditVerifier:
    """Tamper detection via HMAC-SHA256 checksum verification.

    Implements AuditVerifierProtocol. Entries are verified by recomputing
    the HMAC over the canonical persisted row (``entry_to_row``) and
    comparing against the checksum the store read back. Entries written
    before checksums existed carry no stored checksum and are reported
    honestly as unverifiable (``no_checksum_present``) — never silently
    clean, never falsely tampered.

    Args:
        store: Audit store backend (any AuditStoreProtocol implementation).
        config: Audit configuration containing the HMAC key.
    """

    def __init__(
        self,
        store: AuditStoreProtocol,
        config: AuditConfig,
    ) -> None:
        self._store = store
        self._hmac_key = config.hmac_key

    async def verify_recent(self, *, limit: int = 100) -> list[AuditMismatch]:
        """Verify checksums for the most recent entries.

        Args:
            limit: Number of recent entries to verify.

        Returns:
            List of AuditMismatch objects (empty = all verified or not applicable).
        """
        if not self._hmac_key:
            return []

        entries = await self._store.query(AuditQuery(limit=limit))
        logger.debug(
            "audit.verify_recent",
            checked=len(entries),
            hmac_key_set=True,
        )

        mismatches: list[AuditMismatch] = []
        for entry in entries:
            mismatch = await self.verify_entry(entry)
            if mismatch is not None:
                mismatches.append(mismatch)
        return mismatches

    async def verify_entry(self, entry: AuditEntry) -> AuditMismatch | None:
        """Verify checksum for a single entry.

        Recomputed the HMAC over the canonical persisted row and compares
        it against the stored checksum. Older entries may carry v1
        checksums while new entries carry v2; both are accepted. Entries
        with no stored checksum are reported as unverifiable.

        Args:
            entry: The audit entry to verify.

        Returns:
            None when the entry verifies clean; an AuditMismatch whose
            reason is ``checksum_mismatch`` when tampered or
            ``no_checksum_present`` when the entry carries no stored
            checksum and cannot be verified.
        """
        if not self._hmac_key:
            return None

        row = entry_to_row(entry)
        stored = entry.checksum
        if not stored:
            return AuditMismatch(
                entry_id=self._entry_id(entry),
                expected_checksum="",
                actual_checksum=compute_audit_checksum(row, self._hmac_key),
                reason=AuditMismatchReason.NO_CHECKSUM_PRESENT,
            )

        if self._checksum_matches(row, stored):
            return None
        return AuditMismatch(
            entry_id=self._entry_id(entry),
            expected_checksum=stored,
            actual_checksum=compute_audit_checksum(row, self._hmac_key),
        )

    def _checksum_matches(self, row: dict[str, Any], stored: str) -> bool:
        """Compare the stored checksum against both schema versions.

        Write-time checksums are computed at schema version 2 while
        backfilled legacy checksums are computed at version 1, so a
        matching checksum may verify under either version.
        """
        assert self._hmac_key is not None
        return verify_audit_checksum(
            row, self._hmac_key, stored, schema_version=1
        ) or verify_audit_checksum(row, self._hmac_key, stored, schema_version=2)

    def _entry_id(self, entry: AuditEntry) -> str:
        """Return a stable display identifier for an entry."""
        return f"{entry.action}#{entry.occurred_at.isoformat()}"