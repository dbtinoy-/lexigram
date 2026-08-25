"""Delivery-state stores for :class:`~lexigram.notification.delivery.retry.RetryingMailer`.

Two implementations of
:class:`~lexigram.contracts.notification.delivery.DeliveryStoreProtocol`:

- :class:`MemoryDeliveryStore` — in-process, tests/dev.
- :class:`SqlDeliveryStore` — SQL-backed via ``DatabaseProviderProtocol``;
  the table is created automatically on first use (mirrors
  ``DatabaseInboxStore``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_TABLE = "notification_delivery_state"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    delivery_id TEXT        PRIMARY KEY,
    recipient   TEXT        NOT NULL DEFAULT '',
    subject     TEXT        NOT NULL DEFAULT '',
    body        TEXT        NOT NULL DEFAULT '',
    status      TEXT        NOT NULL DEFAULT 'pending',
    attempts    INTEGER     NOT NULL DEFAULT 0,
    last_error  TEXT        NOT NULL DEFAULT '',
    message     JSONB       NOT NULL DEFAULT '{{}}',
    created_at  TIMESTAMPTZ NOT NULL,
    retry_after TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS {table}_status_idx ON {table} (status, retry_after);
"""


class MemoryDeliveryStore:
    """In-process :class:`DeliveryStoreProtocol` for tests/dev."""

    def __init__(self) -> None:
        """Initialise empty stores."""
        self._state: dict[str, dict[str, Any]] = {}
        self._attempts: dict[str, list[dict[str, Any]]] = {}

    async def record_attempt(
        self, delivery_id: str, recipient: str, subject: str, attempt_number: int
    ) -> None:
        """Record one attempt row.

        Args:
            delivery_id: Delivery operation identifier.
            recipient: Comma-separated recipients.
            subject: Message subject.
            attempt_number: 1-based attempt counter.
        """
        self._attempts.setdefault(delivery_id, []).append(
            {
                "recipient": recipient,
                "subject": subject,
                "attempt_number": attempt_number,
                "attempted_at": datetime.now(UTC),
            }
        )

    async def create_pending(self, message: Any) -> str:
        """Persist a pending delivery and return its id.

        Args:
            message: Object exposing ``to``, ``subject``, ``body``.

        Returns:
            Generated delivery identifier.
        """
        delivery_id = str(uuid.uuid4())
        self._state[delivery_id] = {
            "delivery_id": delivery_id,
            "recipient": ",".join(message.to) if getattr(message, "to", None) else "",
            "subject": message.subject,
            "body": message.body,
            "message": {"subject": message.subject, "body": message.body},
            "status": "pending",
            "attempts": 0,
            "last_error": "",
            "created_at": datetime.now(UTC),
            "retry_after": None,
        }
        return delivery_id

    async def mark_delivered(self, delivery_id: str) -> None:
        """Mark a delivery delivered.

        Args:
            delivery_id: Identifier of the delivery operation.
        """
        entry = self._state.get(delivery_id)
        if entry is not None:
            entry["status"] = "delivered"

    async def get_retry_count(self, delivery_id: str) -> int:
        """Return the number of attempts made for a delivery.

        Args:
            delivery_id: Identifier of the delivery operation.

        Returns:
            Current attempt count; 0 when unknown.
        """
        entry = self._state.get(delivery_id)
        return int(entry["attempts"]) if entry else 0

    async def increment_retry(self, delivery_id: str) -> int:
        """Increment and return the attempt counter.

        Args:
            delivery_id: Identifier of the delivery operation.

        Returns:
            New attempt count after incrementing.
        """
        entry = self._state.get(delivery_id)
        if entry is None:
            return 0
        entry["attempts"] = int(entry["attempts"]) + 1
        entry["status"] = "retrying"
        return int(entry["attempts"])

    async def schedule_retry(self, delivery_id: str, delay_seconds: float) -> None:
        """Record when the next retry should run.

        Args:
            delivery_id: Identifier of the delivery operation.
            delay_seconds: Seconds from now.
        """
        entry = self._state.get(delivery_id)
        if entry is not None:
            entry["retry_after"] = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    async def mark_failed(
        self, delivery_id: str, reason: str = "", final: bool = True
    ) -> None:
        """Mark a delivery failed.

        Args:
            delivery_id: Identifier of the delivery operation.
            reason: Human-readable failure description.
            final: Whether retries are exhausted.
        """
        entry = self._state.get(delivery_id)
        if entry is not None:
            entry["status"] = "failed"
            entry["last_error"] = reason

    # -- Worker support (not part of the protocol) ------------------------

    async def due_deliveries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return deliveries whose backoff window has elapsed.

        Args:
            limit: Maximum rows to return.

        Returns:
            Raw state dicts for due, still-retryable deliveries.
        """
        now = datetime.now(UTC)
        due = [
            dict(entry)
            for entry in self._state.values()
            if entry["status"] in ("pending", "retrying")
            and int(entry["attempts"]) < 5
            and (entry["retry_after"] is None or entry["retry_after"] <= now)
        ]
        return sorted(due, key=lambda e: e["created_at"])[:limit]


class SqlDeliveryStore:
    """SQL-backed :class:`DeliveryStoreProtocol` implementation.

    Args:
        db: Database provider injected via DI.
        table: Table name. Defaults to ``notification_delivery_state``.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        *,
        table: str = _DEFAULT_TABLE,
    ) -> None:
        """Initialise with a database provider and table name.

        Args:
            db: Database provider instance.
            table: Backing table name.
        """
        self._db = db
        self._table = table

    async def _ensure_table(self) -> None:
        """Create the backing table/index if absent."""
        sql = _CREATE_TABLE_SQL.format(table=self._table)
        for statement in sql.split(";"):
            if statement.strip():
                await self._db.execute_query(statement)

    @staticmethod
    def _row_to_state(row: Any) -> dict[str, Any]:
        """Normalise a driver row into a plain state dict."""
        return {
            "delivery_id": str(row["delivery_id"]),
            "recipient": str(row.get("recipient") or ""),
            "subject": str(row.get("subject") or ""),
            "body": str(row.get("body") or ""),
            "message": {
                "subject": str(row.get("subject") or ""),
                "body": str(row.get("body") or ""),
            },
            "status": str(row.get("status") or "pending"),
            "attempts": int(row.get("attempts") or 0),
            "last_error": str(row.get("last_error") or ""),
            "created_at": row.get("created_at"),
            "retry_after": row.get("retry_after"),
        }

    async def record_attempt(
        self, delivery_id: str, recipient: str, subject: str, attempt_number: int
    ) -> None:
        """Record one attempt row.

        Args:
            delivery_id: Delivery operation identifier.
            recipient: Comma-separated recipients.
            subject: Message subject.
            attempt_number: 1-based attempt counter.
        """
        await self._db.execute_insert(
            f"{self._table}_attempts",
            {
                "delivery_id": delivery_id,
                "recipient": recipient,
                "subject": subject,
                "attempt_number": attempt_number,
                "attempted_at": datetime.now(UTC),
            },
        )

    async def create_pending(self, message: Any) -> str:
        """Persist a pending delivery row and return its id.

        Args:
            message: Object exposing ``to``, ``subject``, ``body``.

        Returns:
            Generated delivery identifier.
        """
        await self._ensure_table()
        delivery_id = str(uuid.uuid4())
        await self._db.execute_insert(
            self._table,
            {
                "delivery_id": delivery_id,
                "recipient": ",".join(message.to)
                if getattr(message, "to", None)
                else "",
                "subject": message.subject,
                "body": message.body,
                "status": "pending",
                "attempts": 0,
                "last_error": "",
                "message": {"subject": message.subject, "body": message.body},
                "created_at": datetime.now(UTC),
            },
        )
        return delivery_id

    async def mark_delivered(self, delivery_id: str) -> None:
        """Mark a delivery delivered.

        Args:
            delivery_id: Identifier of the delivery operation.
        """
        result = await self._db.execute_update(
            self._table,
            {"status": "delivered"},
            "delivery_id = ?",
            [delivery_id],
        )
        if result.affected_rows == 0:
            logger.warning("delivery_mark_delivered_missing", delivery_id=delivery_id)

    async def get_retry_count(self, delivery_id: str) -> int:
        """Return the attempt counter for a delivery.

        Args:
            delivery_id: Identifier of the delivery operation.

        Returns:
            Current attempt count; 0 when unknown.
        """
        await self._ensure_table()
        result = await self._db.execute_query(
            f"SELECT attempts FROM {self._table} WHERE delivery_id = ?",
            [delivery_id],
        )
        rows = getattr(result, "rows", [])
        return int(rows[0]["attempts"]) if rows else 0

    async def increment_retry(self, delivery_id: str) -> int:
        """Increment and return the attempt counter.

        Args:
            delivery_id: Identifier of the delivery operation.

        Returns:
            New attempt count after incrementing.
        """
        current = await self.get_retry_count(delivery_id)
        new_value = current + 1
        await self._db.execute_update(
            self._table,
            {"attempts": new_value, "status": "retrying"},
            "delivery_id = ?",
            [delivery_id],
        )
        return new_value

    async def schedule_retry(self, delivery_id: str, delay_seconds: float) -> None:
        """Record when the next retry should run.

        Args:
            delivery_id: Identifier of the delivery operation.
            delay_seconds: Seconds from now.
        """
        retry_after = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        await self._db.execute_update(
            self._table,
            {"retry_after": retry_after},
            "delivery_id = ?",
            [delivery_id],
        )

    async def mark_failed(
        self, delivery_id: str, reason: str = "", final: bool = True
    ) -> None:
        """Mark a delivery failed.

        Args:
            delivery_id: Identifier of the delivery operation.
            reason: Human-readable failure description.
            final: Whether retries are exhausted.
        """
        await self._db.execute_update(
            self._table,
            {"status": "failed", "last_error": reason},
            "delivery_id = ?",
            [delivery_id],
        )

    async def due_deliveries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch deliveries whose backoff window has elapsed.

        Args:
            limit: Maximum rows to return.

        Returns:
            Normalised state dicts including a ``message`` payload.
        """
        await self._ensure_table()
        now = datetime.now(UTC)
        result = await self._db.execute_query(
            f"SELECT * FROM {self._table} "
            "WHERE status IN ('pending', 'retrying') AND attempts < 5 "
            "AND (retry_after IS NULL OR retry_after <= ?) "
            "ORDER BY created_at ASC LIMIT ?",
            [now, limit],
        )
        rows = getattr(result, "rows", [])
        states = []
        for row in rows:
            state = self._row_to_state(row)
            raw_message = state["message"]
            if isinstance(raw_message, str):
                from lexigram.serialization import loads

                try:
                    state["message"] = loads(raw_message)
                except (TypeError, ValueError):
                    state["message"] = {}
            states.append(state)
        return states
        return states


__all__ = ["MemoryDeliveryStore", "SqlDeliveryStore"]
