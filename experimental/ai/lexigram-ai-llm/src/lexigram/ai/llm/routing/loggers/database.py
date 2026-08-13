"""Database-backed inference logger for LLM routing.

Persists every ``InferenceLog`` entry to the ``inference_log`` table via
``DatabaseProviderProtocol``.  Suitable for production deployments.

All SQL errors are absorbed so that logging failures never interrupt
inference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.llm.routing.types import InferenceLog
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

__all__ = ["DatabaseInferenceLogger"]

_INSERT_SQL = """
INSERT INTO inference_log (
    routing_id,
    provider,
    model,
    content,
    prompt_tokens,
    completion_tokens,
    is_paid,
    succeeded,
    total_attempts,
    providers_tried,
    context,
    error_message,
    created_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
"""

_GET_RECENT_SQL = """
SELECT
    routing_id,
    provider,
    model,
    content,
    prompt_tokens,
    completion_tokens,
    is_paid,
    succeeded,
    total_attempts,
    providers_tried,
    context,
    error_message,
    created_at
FROM inference_log
ORDER BY created_at DESC
LIMIT $1
"""


class DatabaseInferenceLogger:
    """PostgreSQL-backed inference logger using ``DatabaseProviderProtocol``.

    Every call to :meth:`log` performs a best-effort INSERT; failures are
    swallowed and only emitted as ``ERROR``-level log lines so that
    observability failures never break inference.

    Example:
        >>> db_logger = DatabaseInferenceLogger(db=db_provider)
        >>> await db_logger.log(some_inference_log)
        >>> recent = await db_logger.get_recent(limit=20)
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise the database inference logger.

        Args:
            db: Framework database provider (injected from the DI container).
        """
        self._db = db

    async def log(self, entry: InferenceLog) -> None:
        """Persist one ``InferenceLog`` entry.

        Args:
            entry: :class:`~lexigram.ai.llm.routing.types.InferenceLog` instance.
        """
        try:
            provider = entry.result.provider if entry.result else None
            model = entry.result.model if entry.result else None
            content = entry.result.content if entry.result else None
            prompt_tokens = entry.result.prompt_tokens if entry.result else 0
            completion_tokens = entry.result.completion_tokens if entry.result else 0
            is_paid = entry.result.is_paid if entry.result else False
            error_message = entry.error.message if entry.error else None

            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                await conn.execute(
                    _INSERT_SQL,
                    entry.routing_id,
                    provider,
                    model,
                    content,
                    prompt_tokens,
                    completion_tokens,
                    is_paid,
                    entry.succeeded,
                    entry.total_attempts,
                    entry.providers_tried,
                    dumps_str(entry.context),
                    error_message,
                    entry.created_at,
                )
        except Exception as e:
            logger.exception(
                "llm.inference_log.db: failed to persist routing_id=%s",
                entry.routing_id,
                error=str(e),
            )

    async def get_recent(self, limit: int = 100) -> list[InferenceLog]:
        """Return the most recent *limit* log entries (newest-first).

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of :class:`~lexigram.ai.llm.routing.types.InferenceLog` instances,
            or an empty list on DB error.
        """
        try:
            from lexigram.ai.llm.routing.types import (
                InferenceError,
                InferenceResult,
            )

            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(_GET_RECENT_SQL, limit)

            entries: list[InferenceLog] = []
            for row in rows:
                result: InferenceResult | None = None
                error: InferenceError | None = None

                if row["succeeded"] and row["provider"]:
                    result = InferenceResult(
                        provider=row["provider"],
                        model=row["model"] or "",
                        content=row["content"] or "",
                        prompt_tokens=row["prompt_tokens"] or 0,
                        completion_tokens=row["completion_tokens"] or 0,
                        is_paid=row["is_paid"] or False,
                    )
                elif row["error_message"]:
                    error = InferenceError(
                        message=row["error_message"],
                        providers_tried=list(row["providers_tried"] or []),
                    )

                ctx = row["context"]
                if isinstance(ctx, str):
                    try:
                        ctx = loads(ctx)
                    except (ValueError, KeyError, TypeError):
                        ctx = {}

                entries.append(
                    InferenceLog(
                        routing_id=row["routing_id"],
                        result=result,
                        error=error,
                        providers_tried=list(row["providers_tried"] or []),
                        total_attempts=row["total_attempts"] or 0,
                        context=ctx or {},
                        created_at=row["created_at"],
                    )
                )
            return entries
        except Exception as e:
            logger.exception(
                "llm.inference_log.db: get_recent query failed", error=str(e)
            )
            return []
