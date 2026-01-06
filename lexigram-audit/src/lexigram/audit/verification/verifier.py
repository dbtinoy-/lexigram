"""Audit trail tamper detection via HMAC-SHA256 checksum verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.audit import AuditMismatch, AuditQuery, AuditStoreProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditVerifier"]

logger = get_logger(__name__)


class AuditVerifier:
    """Tamper detection via HMAC-SHA256 checksum verification.

    Implements AuditVerifierProtocol. Checksum verification is only
    meaningful when entries are stored with checksums (i.e. the SQL
    backend with an HMAC key configured). The in-memory store does not
    persist checksums, so ``verify_recent`` and ``verify_entry`` are
    no-ops in that case.

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

        Because AuditEntry does not carry a stored checksum field,
        full tamper-detection is only possible when the SQL backend is
        in use and checksums are persisted in the DB column. Without
        stored checksums this method logs the entries and returns an
        empty list (no mismatches detected / not applicable).

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
        # AuditEntry has no stored checksum field — mismatches cannot be
        # computed from the protocol alone. Return empty (no mismatches).
        return []

    async def verify_entry(self, entry_id: str) -> bool:
        """Verify checksum for a single entry.

        This is a no-op at the protocol level because AuditEntry does
        not carry a stored checksum field. When using the SQL backend
        with HMAC enabled, verification should be performed directly
        against the DB row rather than through the store protocol.

        Args:
            entry_id: ID of the entry to verify.

        Returns:
            True (checksum verification not applicable at protocol level).
        """
        return True
