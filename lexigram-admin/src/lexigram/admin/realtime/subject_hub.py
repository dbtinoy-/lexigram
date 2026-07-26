"""Subject-backed admin event hub.

Same public surface as :class:`lexigram.admin.realtime.sse.AdminEventHub`
but backed by :class:`lexigram.reactive.Subject`, giving subscribers
bounded backpressure and the full operator toolbox.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from lexigram.admin.realtime.sse import AdminEvent, AdminEventType
from lexigram.reactive import Subject, ops


@dataclass(frozen=True)
class _TargetedEvent:
    """Internal envelope pairing an event with its delivery scope.

    ``target_users is None`` means broadcast to every subscriber;
    otherwise delivery is restricted to the listed user ids. This is
    what makes ``target_users``/``user_id`` filtering real instead of
    the no-op it would be if ``Subject`` only ever carried bare
    ``AdminEvent`` values.
    """

    event: AdminEvent
    target_users: tuple[Any, ...] | None


class SubjectAdminEventHub:
    """Fan-out hub for admin events over a reactive Subject.

    Example:
        ```python
        hub = SubjectAdminEventHub()

        async for event in hub.subscribe(resources=["users"]):
            publish_sse(event)

        await hub.publish(AdminEvent(event_type=AdminEventType.RESOURCE_UPDATED, data={}, resource_type="users", resource_id=1))
        ```
    """

    def __init__(self, subject: Subject[_TargetedEvent] | None = None) -> None:
        """Initialize the hub.

        Args:
            subject: Optional shared Subject; defaults to a private one.
        """
        self._subject = subject or Subject[_TargetedEvent]()

    async def subscribe(
        self,
        user_id: Any | None = None,
        resources: list[str] | None = None,
        event_types: list[AdminEventType] | None = None,
    ) -> AsyncGenerator[AdminEvent, None]:
        """Subscribe to filtered admin events.

        Args:
            user_id: Restricts delivery to broadcast events
                (``target_users is None``) plus events explicitly
                targeted at this user. ``None`` (the default) sees only
                broadcast events — matches ``AdminEventHub``'s targeting
                semantics, which ``action_executor.py`` relies on to keep
                a caller's own action-result notification private to
                that caller.
            resources: Optional resource-type filter.
            event_types: Optional event-type filter.

        Yields:
            Matching AdminEvent objects as they are published.
        """
        stream = self._subject.pipe(
            ops.filter(lambda te: te.target_users is None or user_id in te.target_users)
        )
        if resources:
            stream = stream.pipe(
                ops.filter(lambda te: te.event.resource_type in resources)
            )
        if event_types:
            stream = stream.pipe(
                ops.filter(lambda te: te.event.event_type in event_types)
            )
        async for targeted in stream:
            yield targeted.event

    async def publish(
        self,
        event: AdminEvent,
        target_users: list[Any] | None = None,
    ) -> int:
        """Publish an event to active subscribers.

        Args:
            event: Admin event to publish.
            target_users: Restrict delivery to these user ids; ``None``
                (the default) broadcasts to every subscriber.

        Returns:
            Number of active subscriber channels (approximate).
        """
        await self._subject.publish(
            _TargetedEvent(
                event=event,
                target_users=(
                    tuple(target_users) if target_users is not None else None
                ),
            )
        )
        return 1
