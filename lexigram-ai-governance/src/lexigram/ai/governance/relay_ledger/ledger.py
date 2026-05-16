"""Governance relay ledger service: quota credit-in operations.

Journals top-up and check-in credits through the shared ledger store —
the framework records usage but no wallet balance, so credits are
journaled records applications and operators can audit and settle on.
Check-in awards are caller-supplied: amounts and cadences are
application policy, not framework constants.  Every mutation emits a
structured event and returns a domain error value (never raises).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from lexigram.contracts.ai.relay import (
    RelayCheckinRecord,
    RelayLedgerError,
    RelayLedgerServiceProtocol,
    RelayTopUpRecord,
)
from lexigram.identity import ambient as identity
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.governance.relay_ledger.persistence import (
        SqlRelayLedgerStore,
    )
    from lexigram.contracts.ai.governance import RelayUsageScope

logger = get_logger(__name__)

__all__ = ["RelayLedgerService"]


def _validate_amount(amount: str) -> bool:
    """Return whether *amount* is a finite, non-negative decimal."""
    try:
        return Decimal(amount) >= 0
    except (InvalidOperation, ValueError):
        return False


class RelayLedgerService(RelayLedgerServiceProtocol):
    """Credit-in operations over the ledger store.

    Args:
        store: SQL ledger store; the only persistence boundary used.
    """

    def __init__(self, store: SqlRelayLedgerStore) -> None:
        self._store = store

    async def credit(
        self, scope: RelayUsageScope, amount: str, reason: str
    ) -> Result[None, RelayLedgerError]:
        """Journal an immediate completed credit for *scope*.

        Args:
            scope: Accounting scope the credit applies to; the user is
                required.
            amount: Credited amount as a Decimal string.
            reason: Human-readable reason recorded with the journal row.

        Returns:
            ``Ok(None)`` when the credit was journaled, ``Err`` with
            ``invalid_amount`` or ``invalid_scope`` otherwise.
        """
        if scope.user_id is None:
            return Err(
                RelayLedgerError(
                    code="invalid_scope",
                    message="credit requires a user scope",
                )
            )
        if not _validate_amount(amount):
            return Err(
                RelayLedgerError(
                    code="invalid_amount",
                    message="amount must be a non-negative decimal",
                )
            )
        record = RelayTopUpRecord(
            reference_id=f"credit-{identity.new_uuid()}",
            user_id=scope.user_id,
            amount=amount,
            status="completed",
            created_at=clock.now().isoformat(),
        )
        await self._store.insert_topup(record)
        logger.info(
            "relay_ledger.credit",
            user_id=record.user_id,
            amount=amount,
            reason=reason,
        )
        return Ok(None)

    async def settle_topup(
        self, reference_id: str, expected_status: str
    ) -> Result[None, RelayLedgerError]:
        """Flip *reference_id* from *expected_status* to completed exactly once.

        Args:
            reference_id: Top-up reference to settle.
            expected_status: Status the caller observed; only matching
                rows are flipped.

        Returns:
            ``Ok(None)`` on the single successful settle, ``Err`` with
            ``not_found`` or ``stale_settlement`` otherwise.
        """
        flipped = await self._store.settle_topup(reference_id, expected_status)
        if not flipped:
            current = await self._store.topup_status(reference_id)
            if current is None:
                return Err(
                    RelayLedgerError(
                        code="not_found",
                        message=f"top-up {reference_id!r} does not exist",
                    )
                )
            return Err(
                RelayLedgerError(
                    code="stale_settlement",
                    message=(
                        f"top-up {reference_id!r} already settled (status {current!r})"
                    ),
                )
            )
        logger.info(
            "relay_ledger.settle_topup",
            reference_id=reference_id,
            expected_status=expected_status,
        )
        return Ok(None)

    async def checkin(
        self, user_id: str, award: str
    ) -> Result[RelayCheckinRecord, RelayLedgerError]:
        """Award *award* to *user_id* once per UTC day.

        Args:
            user_id: User receiving the award.
            award: Awarded amount as a Decimal string, supplied by the
                caller (application policy).

        Returns:
            ``Ok(record)`` when the award was written, ``Err`` with
            ``already_checked_in`` or ``invalid_amount`` otherwise.
        """
        if not _validate_amount(award):
            return Err(
                RelayLedgerError(
                    code="invalid_amount",
                    message="award must be a non-negative decimal",
                )
            )
        record = RelayCheckinRecord(
            user_id=user_id,
            day=clock.now().date().isoformat(),
            award=award,
            created_at=clock.now().isoformat(),
        )
        written = await self._store.insert_checkin(record)
        if not written:
            return Err(
                RelayLedgerError(
                    code="already_checked_in",
                    message=f"user {user_id!r} already checked in today",
                )
            )
        logger.info(
            "relay_ledger.checkin",
            user_id=record.user_id,
            day=record.day,
            award=record.award,
        )
        return Ok(record)

    async def list_topups(
        self, user_id: str | None, limit: int
    ) -> list[RelayTopUpRecord]:
        """List top-up records, newest first, optionally for one user.

        Args:
            user_id: When set, only this user's records are listed.
            limit: Maximum number of records to return.

        Returns:
            The matching records, newest first.
        """
        if user_id is None:
            return []
        return await self._store.list_topups(user_id, limit)
