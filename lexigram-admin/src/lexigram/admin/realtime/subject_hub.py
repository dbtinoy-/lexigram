"""Subject-backed admin event hub.

The hub the legacy SSE event stream used (``AdminEventHub`` in
``realtime/sse.py``) was retired in the live-widgets plan; this hub
backs both the inbox bridge and the ``/admin/_sse/widgets`` stream via
:class:`lexigram.reactive.Subject`, giving subscribers bounded
backpressure and the full operator toolbox.
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

    ``on_overflow="drop_latest"`` is deliberate: the default
    ``"block"`` mode would suspend ``publish()`` itself — and thus every
    caller awaiting it, including a write-action HTTP response — on one
    slow subscriber. A dropped live delta is recoverable by the next
    reconcile-on-load snapshot; a blocked publisher is not.

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
            subject: Optional shared Subject; defaults to a private one
                with ``on_overflow="drop_latest"``.
        """
        self._subject = subject or Subject[_TargetedEvent](on_overflow="drop_latest")

    async def subscribe(
        self,
        user_id: Any | None = None,
        resources: list[str] | None = None,
        event_types: list[AdminEventType] | None = None,
        tenant_id: str | None = None,
    ) -> AsyncGenerator[AdminEvent, None]:
        """Subscribe to filtered admin events.

        Args:
            user_id: Restricts delivery to broadcast events
                (``target_users is None``) plus events explicitly
                targeted at this user. ``None`` (the default) sees only
                broadcast events — matches the legacy hub's targeting
                semantics, which ``action_executor.py`` relies on to keep
                a caller's own action-result notification private to
                that caller.
            resources: Optional resource-type filter. Caller is
                responsible for authorizing which resources the
                subscriber may request — this hub applies the filter,
                it does not authorize it (see the SSE route handler).
            event_types: Optional event-type filter.
            tenant_id: Restricts delivery to events with no ``tenant_id``
                (untenanted / framework-level) plus events whose
                ``tenant_id`` matches. ``None`` sees only untenanted
                events.

        Yields:
            Matching AdminEvent objects as they are published.
        """
        stream = self._subject.pipe(
            ops.filter(lambda te: te.target_users is None or user_id in te.target_users)
        )
        stream = stream.pipe(
            ops.filter(
                lambda te: te.event.tenant_id is None or te.event.tenant_id == tenant_id
            )
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

    async def publish_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        target_users: list[Any] | None = None,
    ) -> int:
        """Publish a notification event.

        Produces an ``AdminEventType.NOTIFICATION`` broadcast to the
        given users (or everyone when ``target_users`` is ``None``),
        mirroring the retired legacy hub's call signature so
        callers (the inbox bridge, action-result notifications) can move
        to this hub with no call-site changes beyond the import.
        """
        event = AdminEvent(
            event_type=AdminEventType.NOTIFICATION,
            data={"title": title, "message": message, "level": level},
        )
        return await self.publish(event, target_users=target_users)
