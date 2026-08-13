"""Admin action handlers for the queue contributor.

Each handler accepts ``(container, **params)`` per the admin action
contract and returns a result dict describing the outcome. The
``container`` resolves ``DeadLetterQueue`` and ``QueueProtocol`` lazily
at invocation time.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger
from lexigram.queue.core.dlq import DeadLetterEntry, DeadLetterQueue

logger = get_logger(__name__)


async def retry_failed(container: Any, **params: object) -> dict[str, object]:
    """Re-publish every message currently tracked in the dead letter queue.

    Drains the DLQ and publishes each entry's original message back to
    its original topic. Entries whose publish fails are pushed back into
    the DLQ so they are never lost.

    Args:
        container: Container resolver exposing ``DeadLetterQueue`` and
            ``QueueProtocol``.
        **params: Unused action parameters.

    Returns:
        Mapping describing the outcome: ``ok`` bool, ``message`` and
        ``echo`` with ``retried``/``failed`` counts.
    """
    dlq = await container.resolve_optional(DeadLetterQueue)
    if dlq is None:
        return {
            "ok": False,
            "message": "dead letter queue is not registered",
            "echo": {},
        }
    queue = await container.resolve_optional(QueueProtocol)
    if queue is None:
        return {
            "ok": False,
            "message": "queue backend is not registered",
            "echo": {},
        }
    entries = await dlq.drain()
    if not entries:
        return {
            "ok": True,
            "message": "no failed messages to retry",
            "echo": {"retried": 0, "failed": 0},
        }
    results = await asyncio.gather(
        *[queue.publish(entry.message.topic, entry.message) for entry in entries],
        return_exceptions=True,
    )
    failed_entries: list[tuple[DeadLetterEntry, Exception]] = [
        (entry, result)
        for entry, result in zip(entries, results, strict=False)
        if isinstance(result, Exception)
    ]
    for entry, error in failed_entries:
        await dlq.push(entry.message, str(error))
    retried = len(entries) - len(failed_entries)
    if failed_entries:
        logger.warning(
            "queue_admin.retry_failed.partial",
            retried=retried,
            failed=len(failed_entries),
        )
        return {
            "ok": False,
            "message": (
                f"retried {retried} of {len(entries)} failed messages; "
                f"{len(failed_entries)} publish failed"
            ),
            "echo": {"retried": retried, "failed": len(failed_entries)},
        }
    logger.info("queue_admin.retry_failed", retried=retried)
    return {
        "ok": True,
        "message": f"retried {retried} of {len(entries)} failed messages",
        "echo": {"retried": retried, "failed": 0},
    }


__all__ = ["retry_failed"]
