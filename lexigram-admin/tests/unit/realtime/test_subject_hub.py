"""Tests for the subject-backed admin event hub."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.admin.realtime.sse import AdminEvent, AdminEventType
from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub


def make_event(event_type: AdminEventType, resource: str = "users") -> AdminEvent:
    return AdminEvent(
        event_type=event_type,
        data={},
        resource_type=resource,
        resource_id=1,
    )


@pytest.mark.asyncio
async def test_subject_hub_delivers_filtered_events() -> None:
    hub = SubjectAdminEventHub()
    received: list[AdminEvent] = []

    async def consumer() -> None:
        async for event in hub.subscribe(resources=["users"], event_types=[AdminEventType.RESOURCE_UPDATED]):
            received.append(event)

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.02)
    await hub.publish(make_event(AdminEventType.RESOURCE_UPDATED))
    await hub.publish(make_event(AdminEventType.RESOURCE_CREATED))
    await hub.publish(make_event(AdminEventType.RESOURCE_UPDATED, resource="orders"))
    await hub.publish(make_event(AdminEventType.RESOURCE_UPDATED))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(received) == 2
    assert all(e.resource_type == "users" for e in received)


@pytest.mark.asyncio
async def test_subject_hub_respects_target_users() -> None:
    """Regression test for the AdminEventHub targeting parity requirement.

    ``action_executor.py`` publishes each admin's own action-result
    notification with ``target_users=[caller_id]`` so other admins never
    see it. A hub that ignores ``target_users``/``user_id`` broadcasts
    that notification to everyone — a confidentiality regression.
    """
    hub = SubjectAdminEventHub()
    received_a: list[AdminEvent] = []
    received_b: list[AdminEvent] = []

    async def consume(user_id: str, sink: list[AdminEvent]) -> None:
        async for event in hub.subscribe(user_id=user_id):
            sink.append(event)

    task_a = asyncio.create_task(consume("admin-a", received_a))
    task_b = asyncio.create_task(consume("admin-b", received_b))
    await asyncio.sleep(0.02)
    await hub.publish(make_event(AdminEventType.RESOURCE_UPDATED), target_users=["admin-a"])
    await hub.publish(make_event(AdminEventType.RESOURCE_CREATED))  # broadcast (no target_users)
    await asyncio.sleep(0.02)
    task_a.cancel()
    task_b.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task_a
    with pytest.raises(asyncio.CancelledError):
        await task_b
    # admin-a sees the event targeted at them plus the broadcast; admin-b sees only the broadcast.
    assert [e.event_type for e in received_a] == [
        AdminEventType.RESOURCE_UPDATED,
        AdminEventType.RESOURCE_CREATED,
    ]
    assert [e.event_type for e in received_b] == [AdminEventType.RESOURCE_CREATED]


@pytest.mark.asyncio
async def test_subject_hub_uses_drop_latest_overflow() -> None:
    """Fan-out must never block the publisher on one slow subscriber.

    Regression guard for the head-of-line-blocking risk: Subject's class
    default is on_overflow="block", which would suspend publish() itself
    on a full subscriber channel. A hub used for both widget delivery and
    synchronous notification-after-write-action delivery cannot afford
    that.
    """
    hub = SubjectAdminEventHub()
    assert hub._subject._on_overflow == "drop_latest"  # noqa: SLF001


@pytest.mark.asyncio
async def test_subject_hub_filters_by_tenant() -> None:
    hub = SubjectAdminEventHub()
    received_acme: list[AdminEvent] = []
    received_other: list[AdminEvent] = []

    async def consume(tenant_id: str, sink: list[AdminEvent]) -> None:
        async for event in hub.subscribe(tenant_id=tenant_id):
            sink.append(event)

    task_acme = asyncio.create_task(consume("acme", received_acme))
    task_other = asyncio.create_task(consume("other-co", received_other))
    await asyncio.sleep(0.02)
    acme_event = make_event(AdminEventType.RESOURCE_UPDATED)
    acme_event.tenant_id = "acme"
    await hub.publish(acme_event)
    await asyncio.sleep(0.02)
    task_acme.cancel()
    task_other.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task_acme
    with pytest.raises(asyncio.CancelledError):
        await task_other
    assert len(received_acme) == 1
    assert received_other == []


@pytest.mark.asyncio
async def test_subject_hub_untenanted_event_visible_to_any_subscriber() -> None:
    """Events with no tenant_id (e.g. framework-level notices) are broadcast."""
    hub = SubjectAdminEventHub()
    received: list[AdminEvent] = []

    async def consume() -> None:
        async for event in hub.subscribe(tenant_id="acme"):
            received.append(event)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.02)
    await hub.publish(make_event(AdminEventType.RESOURCE_UPDATED))  # tenant_id=None
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(received) == 1


@pytest.mark.asyncio
async def test_subject_hub_publish_notification() -> None:
    """publish_notification mirrors AdminEventHub's convenience signature."""
    hub = SubjectAdminEventHub()
    received: list[AdminEvent] = []

    async def consume() -> None:
        async for event in hub.subscribe(user_id="admin-a"):
            received.append(event)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.02)
    await hub.publish_notification(
        title="Action completed",
        message="ok",
        level="success",
        target_users=["admin-a"],
    )
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(received) == 1
    assert received[0].event_type == AdminEventType.NOTIFICATION
    assert received[0].data == {"title": "Action completed", "message": "ok", "level": "success"}
