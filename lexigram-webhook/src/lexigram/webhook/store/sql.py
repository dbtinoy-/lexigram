"""SQL-backed webhook stores (requires lexigram-webhook[sql])."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookSubscription,
)
from lexigram.logging import get_logger
import lexigram.serialization as json

__all__ = ["SqlWebhookDeliveryStore", "SqlWebhookSubscriptionStore"]

logger = get_logger(__name__)


def _naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize to a naive UTC datetime for TIMESTAMP columns."""
    if dt is None:
        return None
    return dt if dt.tzinfo is None else dt.astimezone(UTC).replace(tzinfo=None)


_SUBSCRIPTION_DDL = """
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    subscription_id VARCHAR(255) PRIMARY KEY,
    url             TEXT         NOT NULL,
    secret          VARCHAR(512) NOT NULL,
    event_types     TEXT,
    active          BOOLEAN      NOT NULL DEFAULT TRUE,
    description     TEXT         NOT NULL DEFAULT '',
    tenant_id       VARCHAR(255),
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata        TEXT         NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ws_active ON webhook_subscriptions(active);
CREATE INDEX IF NOT EXISTS idx_ws_tenant ON webhook_subscriptions(tenant_id)
"""

_DELIVERY_DDL = """
CREATE TABLE IF NOT EXISTS webhook_delivery_attempts (
    attempt_id       VARCHAR(255) PRIMARY KEY,
    subscription_id  VARCHAR(255) NOT NULL,
    event_id         VARCHAR(255) NOT NULL,
    event_type       VARCHAR(255) NOT NULL,
    status           VARCHAR(50)  NOT NULL DEFAULT 'pending',
    status_code      INTEGER,
    attempt_number   INTEGER      NOT NULL DEFAULT 1,
    attempted_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    next_retry_at    TIMESTAMP,
    error_message    TEXT,
    duration_ms      REAL
);
CREATE INDEX IF NOT EXISTS idx_wda_sub ON webhook_delivery_attempts(subscription_id);
CREATE INDEX IF NOT EXISTS idx_wda_event ON webhook_delivery_attempts(event_id);
CREATE INDEX IF NOT EXISTS idx_wda_status ON webhook_delivery_attempts(status);
CREATE INDEX IF NOT EXISTS idx_wda_attempted_at ON webhook_delivery_attempts(attempted_at)
"""


class SqlWebhookSubscriptionStore:
    """SQL-backed webhook subscription store.

    Requires ``lexigram-webhook[sql]`` extra and a ``DatabaseProviderProtocol``.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialize with database provider.

        Args:
            db: Database provider for query execution.
        """
        self._db = db

    async def initialize(self) -> None:
        """Create the webhook_subscriptions table and indexes if they do not exist."""
        for statement in _SUBSCRIPTION_DDL.split(";"):
            stmt = statement.strip()
            if stmt:
                await self._db.execute_query(stmt)
        logger.info("webhook_subscriptions_table_created")

    async def create(self, subscription: WebhookSubscription) -> None:
        """Persist a new subscription.

        Args:
            subscription: Subscription to store.
        """
        event_types = (
            json.dumps_str(sorted(subscription.event_types))
            if subscription.event_types is not None
            else None
        )
        sql = (
            "INSERT INTO webhook_subscriptions "
            "(subscription_id, url, secret, event_types, active, description, "
            "tenant_id, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            subscription.subscription_id,
            subscription.url,
            subscription.secret,
            event_types,
            int(subscription.active),
            subscription.description,
            subscription.tenant_id,
            _naive_utc(subscription.created_at),
            json.dumps_str(subscription.metadata),
        ]
        await self._db.execute_query(sql, params)

    async def get(self, subscription_id: str) -> WebhookSubscription | None:
        """Return subscription by ID, or None.

        Args:
            subscription_id: UUID to look up.

        Returns:
            The subscription if found, else None.
        """
        sql = "SELECT * FROM webhook_subscriptions WHERE subscription_id = ?"
        result = await self._db.execute_query(sql, [subscription_id])
        if not result.rows:
            return None
        return self._row_to_subscription(result.rows[0])

    async def list(
        self,
        *,
        active_only: bool = True,
        event_type: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        """List subscriptions matching filters.

        Args:
            active_only: Only return active subscriptions.
            event_type: Filter to subscriptions that handle this event type.
            tenant_id: Filter by tenant.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Filtered and paginated subscriptions ordered by created_at DESC.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if active_only:
            conditions.append("active = ?")
            params.append(1)

        if tenant_id is not None:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)

        if event_type is not None:
            conditions.append("(event_types IS NULL OR event_types LIKE ?)")
            params.append(f'%"{event_type}"%')

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            f"SELECT * FROM webhook_subscriptions {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        result = await self._db.execute_query(sql, params)
        if not result.success:
            return []
        return [self._row_to_subscription(row) for row in result.rows]

    async def update(self, subscription: WebhookSubscription) -> None:
        """Update an existing subscription.

        Args:
            subscription: Updated subscription data.
        """
        event_types = (
            json.dumps_str(sorted(subscription.event_types))
            if subscription.event_types is not None
            else None
        )
        sql = (
            "UPDATE webhook_subscriptions SET "
            "url = ?, secret = ?, event_types = ?, active = ?, "
            "description = ?, tenant_id = ?, metadata = ? "
            "WHERE subscription_id = ?"
        )
        params = [
            subscription.url,
            subscription.secret,
            event_types,
            int(subscription.active),
            subscription.description,
            subscription.tenant_id,
            json.dumps_str(subscription.metadata),
            subscription.subscription_id,
        ]
        await self._db.execute_query(sql, params)

    async def delete(self, subscription_id: str) -> None:
        """Remove a subscription.

        Args:
            subscription_id: UUID to remove.
        """
        sql = "DELETE FROM webhook_subscriptions WHERE subscription_id = ?"
        await self._db.execute_query(sql, [subscription_id])

    def _row_to_subscription(self, row: dict[str, Any]) -> WebhookSubscription:
        """Convert a database row dict to a WebhookSubscription.

        Args:
            row: Raw row dict from the database.

        Returns:
            Deserialized WebhookSubscription instance.
        """
        raw_types = row.get("event_types")
        event_types = (
            frozenset(json.loads(raw_types)) if raw_types is not None else None
        )
        raw_meta = row.get("metadata")
        metadata = json.loads(raw_meta) if raw_meta else {}
        return WebhookSubscription(
            subscription_id=row["subscription_id"],
            url=row["url"],
            secret=row["secret"],
            event_types=event_types,
            active=bool(row.get("active", True)),
            description=row.get("description", ""),
            tenant_id=row.get("tenant_id"),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if isinstance(row["created_at"], str)
                else row["created_at"]
            ),
            metadata=metadata,
        )


class SqlWebhookDeliveryStore:
    """SQL-backed webhook delivery attempt store.

    Requires ``lexigram-webhook[sql]`` extra and a ``DatabaseProviderProtocol``.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialize with database provider.

        Args:
            db: Database provider for query execution.
        """
        self._db = db

    async def initialize(self) -> None:
        """Create the webhook_delivery_attempts table and indexes if they do not exist."""
        for statement in _DELIVERY_DDL.split(";"):
            stmt = statement.strip()
            if stmt:
                await self._db.execute_query(stmt)

    async def record_attempt(self, attempt: DeliveryAttempt) -> None:
        """Persist a delivery attempt record.

        Args:
            attempt: Attempt to record.
        """
        sql = (
            "INSERT INTO webhook_delivery_attempts "
            "(attempt_id, subscription_id, event_id, event_type, status, "
            "status_code, attempt_number, attempted_at, next_retry_at, "
            "error_message, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            attempt.attempt_id,
            attempt.subscription_id,
            attempt.event_id,
            attempt.event_type,
            attempt.status.value,
            attempt.status_code,
            attempt.attempt_number,
            _naive_utc(attempt.attempted_at),
            _naive_utc(attempt.next_retry_at),
            attempt.error_message,
            attempt.duration_ms,
        ]
        await self._db.execute_query(sql, params)

    async def get_attempts(
        self,
        *,
        subscription_id: str | None = None,
        event_id: str | None = None,
        status: DeliveryStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryAttempt]:
        """Query delivery attempts matching filters, newest-first.

        Args:
            subscription_id: Filter by subscription.
            event_id: Filter by event.
            status: Filter by delivery status.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Matching attempts in newest-first order.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if subscription_id is not None:
            conditions.append("subscription_id = ?")
            params.append(subscription_id)

        if event_id is not None:
            conditions.append("event_id = ?")
            params.append(event_id)

        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            f"SELECT * FROM webhook_delivery_attempts {where} "
            f"ORDER BY attempted_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        result = await self._db.execute_query(sql, params)
        if not result.success:
            return []
        return [self._row_to_attempt(row) for row in result.rows]

    async def get_dead_letters(
        self,
        *,
        subscription_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryAttempt]:
        """Return attempts in dead-letter status.

        Args:
            subscription_id: Optional filter by subscription.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Dead-lettered attempts.
        """
        return await self.get_attempts(
            subscription_id=subscription_id,
            status=DeliveryStatus.DEAD_LETTER,
            limit=limit,
            offset=offset,
        )

    async def count_recent_failures(
        self,
        subscription_id: str,
        since: datetime,
    ) -> int:
        """Count failed attempts for a subscription since a given time.

        Args:
            subscription_id: Subscription to check.
            since: Count attempts after this timestamp.

        Returns:
            Count of failed attempts.
        """
        sql = (
            "SELECT COUNT(*) AS count FROM webhook_delivery_attempts "
            "WHERE subscription_id = ? AND status IN (?, ?) AND attempted_at >= ?"
        )
        params = [
            subscription_id,
            DeliveryStatus.FAILED.value,
            DeliveryStatus.DEAD_LETTER.value,
            _naive_utc(since),
        ]
        result = await self._db.execute_query(sql, params)
        if not result.success or not result.rows:
            return 0
        return int(result.rows[0]["count"])

    def _row_to_attempt(self, row: dict[str, Any]) -> DeliveryAttempt:
        """Convert a database row dict to a DeliveryAttempt.

        Args:
            row: Raw row dict from the database.

        Returns:
            Deserialized DeliveryAttempt instance.
        """

        def parse_dt(v: Any) -> datetime:
            return datetime.fromisoformat(v) if isinstance(v, str) else v

        return DeliveryAttempt(
            attempt_id=row["attempt_id"],
            subscription_id=row["subscription_id"],
            event_id=row["event_id"],
            event_type=row["event_type"],
            status=DeliveryStatus(row["status"]),
            status_code=row.get("status_code"),
            attempt_number=int(row.get("attempt_number", 1)),
            attempted_at=parse_dt(row["attempted_at"]),
            next_retry_at=parse_dt(row["next_retry_at"])
            if row.get("next_retry_at")
            else None,
            error_message=row.get("error_message"),
            duration_ms=row.get("duration_ms"),
        )
