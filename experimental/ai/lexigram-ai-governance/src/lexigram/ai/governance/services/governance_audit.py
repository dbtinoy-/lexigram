"""Fire-and-forget audit emission for governance decisions.

Audit recording must never block or fail a governance check: events are
scheduled on the running loop as background tasks and silently dropped
when no audit store is configured or no loop is running.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.ai.governance.audit import AIAuditStore

logger = get_logger(__name__)

__all__ = ["emit_audit_event", "notify_soft_limit"]


def emit_audit_event(
    store: AIAuditStore | None,
    background_tasks: set[asyncio.Task[object]],
    event_type: str,
    *,
    model: str | None = None,
    provider: str | None = None,
    user_id: str | None = None,
    status: str = "success",
    tokens: int | None = None,
    cost: float | None = None,
    latency_ms: float | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Schedule an audit event on the running loop without blocking.

    Creates an :class:`~lexigram.ai.governance.audit.AIAuditEvent` and
    schedules ``record()`` on the audit store.  Silently drops the event
    when no audit store is configured or no event loop is running.

    Args:
        store: The audit store, or ``None`` to disable auditing.
        background_tasks: Owner's task set; finished tasks are discarded
            from it to keep strong references alive (RUF006).
        event_type: Audit event type name (an :class:`AuditEventType` value).
        model: Model involved in the decision, if any.
        provider: Provider involved in the decision, if any.
        user_id: User the decision applies to, if any.
        status: Outcome status (``"success"``, ``"denied"``, ...).
        tokens: Token count associated with the event, if any.
        cost: Cost associated with the event, if any.
        latency_ms: Latency associated with the event, if any.
        metadata: Additional structured context copied into the event.
    """
    if store is None:
        return

    from lexigram.ai.governance.audit import AIAuditEvent, AuditEventType

    event = AIAuditEvent(
        event_type=AuditEventType(event_type),
        model=model,
        provider=provider,
        user_id=user_id,
        status=status,
        tokens=tokens,
        cost=cost,
        latency_ms=latency_ms,
        metadata=dict(metadata) if metadata else {},
    )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    task = loop.create_task(store.record(event))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def notify_soft_limit(
    callback: Callable[..., object] | None,
    background_tasks: set[asyncio.Task[object]],
    user_id: str | None,
    current: float,
    budget: float,
) -> None:
    """Invoke the soft-limit callback, scheduling awaitables in background.

    Args:
        callback: The ``on_soft_limit`` callback, or ``None`` (no-op).
        background_tasks: Owner's task set; finished tasks are discarded
            from it to keep strong references alive (RUF006).
        user_id: User that crossed the soft limit.
        current: Current monthly spend.
        budget: Configured monthly budget.
    """
    if callback is None:
        return
    import inspect

    result = callback(user_id, current, budget)
    if inspect.isawaitable(result):
        task = asyncio.ensure_future(result)
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
