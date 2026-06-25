"""SQL-backed feedback store using :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.

Records all four feedback types, extracts ``session_id`` from item context
into a dedicated column for efficient session-scoped queries, and serialises
``value``/``context``/``metadata`` as JSON strings.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from lexigram.ai.feedback.exceptions import FeedbackError
from lexigram.ai.feedback.storage.protocols import FeedbackSummary
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_feedback (
    id          TEXT    NOT NULL PRIMARY KEY,
    type        TEXT    NOT NULL,
    value       TEXT    NOT NULL,
    context     TEXT    NOT NULL DEFAULT '{}',
    metadata    TEXT    NOT NULL DEFAULT '{}',
    session_id  TEXT,
    owner_id    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
)
"""

_CREATE_IDX_OWNER = (
    "CREATE INDEX IF NOT EXISTS idx_ai_feedback_owner ON ai_feedback (owner_id)"
)
_CREATE_IDX_SESSION = (
    "CREATE INDEX IF NOT EXISTS idx_ai_feedback_session ON ai_feedback (session_id)"
)
_CREATE_IDX_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_ai_feedback_type ON ai_feedback (type)"
)
_CREATE_IDX_CREATED = (
    "CREATE INDEX IF NOT EXISTS idx_ai_feedback_created_at ON ai_feedback (created_at)"
)

_INSERT = (
    "INSERT OR IGNORE INTO ai_feedback "
    "(id, type, value, context, metadata, session_id, owner_id, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)


class DatabaseFeedbackStore:
    """Persist and query feedback items via :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.

    The backing table (``ai_feedback``) is created lazily on first write.
    Indexed columns: ``session_id``, ``type``, ``created_at``.

    Args:
        provider: DI-injected database provider.
    """

    def __init__(self, provider: DatabaseProviderProtocol) -> None:
        self._db = provider
        self._initialised = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _ensure_table(self) -> None:
        """Create backing table + indexes on first use."""
        if self._initialised:
            return
        await self._db.execute(_CREATE_TABLE)
        await self._db.execute(_CREATE_IDX_OWNER)
        await self._db.execute(_CREATE_IDX_SESSION)
        await self._db.execute(_CREATE_IDX_TYPE)
        await self._db.execute(_CREATE_IDX_CREATED)
        self._initialised = True

    # ------------------------------------------------------------------
    # FeedbackStoreProtocol implementation
    # ------------------------------------------------------------------

    async def save(self, feedback: FeedbackItem) -> Result[str, FeedbackError]:
        """Persist *feedback* and return its ID on success.

        Args:
            feedback: Item to store.

        Returns:
            ``Ok(feedback.id)`` on success, ``Err(FeedbackError)`` on failure.
        """
        try:
            await self._ensure_table()
            session_id: str | None = feedback.context.get("session_id")
            await self._db.execute(
                _INSERT,
                [
                    feedback.id,
                    feedback.feedback_type.value,
                    dumps_str(feedback.value),
                    dumps_str(feedback.context),
                    dumps_str(feedback.metadata),
                    session_id,
                    feedback.owner_id,
                    feedback.created_at.isoformat(),
                ],
            )
            return Ok(feedback.id)
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.error(
                "feedback_save_failed", feedback_id=feedback.id, error=str(exc)
            )
            return Err(FeedbackError(f"Failed to save feedback {feedback.id}: {exc}"))

    async def find_by_session(
        self, session_id: str, *, owner_id: str
    ) -> list[FeedbackItem]:
        """Return all items collected during *session_id* for *owner_id*, newest first.

        Args:
            session_id: Session identifier to filter by.
            owner_id: Owner scope; only this owner's items are returned.

        Returns:
            Matching feedback items ordered by creation time descending.
        """
        await self._ensure_table()
        result = await self._db.execute_query(
            "SELECT * FROM ai_feedback WHERE session_id = ? AND owner_id = ? "
            "ORDER BY created_at DESC",
            [session_id, owner_id],
        )
        return [self._row_to_item(row) for row in result.rows]

    async def find_by_type(
        self,
        feedback_type: FeedbackType,
        *,
        owner_id: str,
        limit: int = 100,
    ) -> list[FeedbackItem]:
        """Return feedback items of *feedback_type* for *owner_id*, newest first.

        Args:
            feedback_type: Type to filter by.
            owner_id: Owner scope; only this owner's items are returned.
            limit: Maximum number of results (default: 100).

        Returns:
            Matching feedback items ordered by creation time descending.
        """
        await self._ensure_table()
        result = await self._db.execute_query(
            "SELECT * FROM ai_feedback WHERE type = ? AND owner_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            [feedback_type.value, owner_id, limit],
        )
        return [self._row_to_item(row) for row in result.rows]

    async def aggregate(
        self, *, owner_id: str, window_hours: int = 24
    ) -> FeedbackSummary:
        """Compute summary statistics for *owner_id* in the last *window_hours* hours.

        Args:
            owner_id: Owner scope; only this owner's items are aggregated.
            window_hours: Look-back window in hours (default: 24).

        Returns:
            Aggregated :class:`FeedbackSummary` for the window.
        """
        await self._ensure_table()
        since = (datetime.now(UTC) - timedelta(hours=window_hours)).isoformat()

        # Total count
        count_result = await self._db.execute_query(
            "SELECT COUNT(*) AS cnt FROM ai_feedback "
            "WHERE created_at >= ? AND owner_id = ?",
            [since, owner_id],
        )
        total = int((count_result.rows[0] or {}).get("cnt", 0))

        # Average rating
        avg_result = await self._db.execute_query(
            "SELECT AVG(CAST(value AS REAL)) AS avg_rating "
            "FROM ai_feedback WHERE type = ? AND created_at >= ? AND owner_id = ?",
            [FeedbackType.RATING.value, since, owner_id],
        )
        raw_avg = (avg_result.rows[0] or {}).get("avg_rating")
        average_rating = float(raw_avg) if raw_avg is not None else None

        # Count by type
        type_result = await self._db.execute_query(
            "SELECT type, COUNT(*) AS cnt FROM ai_feedback "
            "WHERE created_at >= ? AND owner_id = ? GROUP BY type",
            [since, owner_id],
        )
        count_by_type = {row["type"]: int(row["cnt"]) for row in type_result.rows}

        return FeedbackSummary(
            total_count=total,
            average_rating=average_rating,
            count_by_type=count_by_type,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_item(row: Any) -> FeedbackItem:
        """Deserialise a database row back into a :class:`FeedbackItem`.

        Args:
            row: Raw row dict from the database.

        Returns:
            Reconstructed :class:`FeedbackItem`.
        """
        try:
            value: Any = loads_str(row["value"])
        except (ValueError, TypeError):
            value = row["value"]

        try:
            context: dict[str, Any] = loads_str(row["context"]) or {}
        except (ValueError, TypeError):
            context = {}

        try:
            metadata: dict[str, Any] = loads_str(row["metadata"]) or {}
        except (ValueError, TypeError):
            metadata = {}

        return FeedbackItem(
            feedback_type=FeedbackType(row["type"]),
            value=value,
            owner_id=str(row["owner_id"]),
            context=context,
            metadata=metadata,
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


__all__ = ["DatabaseFeedbackStore"]
