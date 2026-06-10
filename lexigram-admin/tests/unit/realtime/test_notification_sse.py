"""Tests for the admin SSE event hub (AdminEventHub)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.admin.realtime import (
    AdminEvent,
    AdminEventHub,
    AdminEventType,
)


async def start_subscription(
    hub: AdminEventHub,
    **kwargs: Any,
) -> tuple[Any, asyncio.Task[Any]]:
    """Register a subscriber by priming its first ``__anext__`` call.

    The async generator body (which registers the subscriber) only runs on
    the first ``__anext__``, so the call is scheduled as a task and the
    event loop is allowed to register it before publishing.

    Returns:
        (subscription, task) where the task resolves to the first event
        the subscriber receives.
    """
    subscription = hub.subscribe(**kwargs)
    task = asyncio.create_task(subscription.__anext__())
    await asyncio.sleep(0)
    return subscription, task


async def close_subscription(subscription: Any, task: asyncio.Task[Any]) -> None:
    """Cancel any pending receive and close the subscription."""
    if not task.done():
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    await subscription.aclose()


@pytest.mark.asyncio
async def test_subscribe_receives_published_event() -> None:
    hub = AdminEventHub()
    subscription, task = await start_subscription(hub, resources=["users"])

    delivered = await hub.publish_resource_event(
        AdminEventType.RESOURCE_UPDATED,
        resource_type="users",
        resource_id=42,
        data={"changes": {"name": "x"}},
    )
    event = await task

    assert delivered == 1
    assert event.event_type == AdminEventType.RESOURCE_UPDATED
    assert event.resource_type == "users"
    assert event.resource_id == 42
    assert event.data["changes"] == {"name": "x"}

    await close_subscription(subscription, task)


@pytest.mark.asyncio
async def test_publish_returns_delivery_count() -> None:
    hub = AdminEventHub()
    sub1, task1 = await start_subscription(hub)
    sub2, task2 = await start_subscription(hub)

    delivered = await hub.publish(
        AdminEvent(event_type=AdminEventType.NOTIFICATION, data={"title": "hi"}),
    )

    assert delivered == 2
    await task1
    await task2

    await close_subscription(sub1, task1)
    await close_subscription(sub2, task2)


@pytest.mark.asyncio
async def test_publish_targets_specific_users() -> None:
    hub = AdminEventHub()
    alice, alice_task = await start_subscription(hub, user_id="alice")
    bob, bob_task = await start_subscription(hub, user_id="bob")

    delivered = await hub.publish_notification(
        title="For alice only",
        message="secret",
        target_users=["alice"],
    )

    assert delivered == 1
    event = await alice_task
    assert event.event_type == AdminEventType.NOTIFICATION
    assert event.data["title"] == "For alice only"

    await close_subscription(bob, bob_task)
    await close_subscription(alice, alice_task)


@pytest.mark.asyncio
async def test_publish_routes_to_resource_subscribers() -> None:
    hub = AdminEventHub()
    users_sub, users_task = await start_subscription(hub, resources=["users"])
    posts_sub, posts_task = await start_subscription(hub, resources=["posts"])

    delivered = await hub.publish_resource_event(
        AdminEventType.RESOURCE_CREATED,
        resource_type="users",
        resource_id=7,
        data={"name": "new-user"},
    )

    assert delivered == 1
    event = await users_task
    assert event.resource_type == "users"

    await close_subscription(posts_sub, posts_task)
    await close_subscription(users_sub, users_task)


@pytest.mark.asyncio
async def test_subscribe_filters_by_event_type() -> None:
    hub = AdminEventHub()
    subscription, task = await start_subscription(
        hub, event_types=[AdminEventType.TOAST]
    )

    await hub.publish(
        AdminEvent(event_type=AdminEventType.NOTIFICATION, data={"title": "n"}),
    )
    delivered = await hub.publish_toast(message="t", variant="success")
    event = await task

    assert delivered == 1
    assert event.event_type == AdminEventType.TOAST

    await close_subscription(subscription, task)


@pytest.mark.asyncio
async def test_subscriber_cleaned_up_on_disconnect() -> None:
    hub = AdminEventHub()
    subscription = hub.subscribe(resources=["users"], user_id="alice")
    await subscription.aclose()

    assert hub._subscribers == {}
    assert hub._resource_subscriptions == {}
    assert hub._user_subscriptions == {}


@pytest.mark.asyncio
async def test_event_to_dict_shape() -> None:
    event = AdminEvent(
        event_type=AdminEventType.NOTIFICATION,
        data={"title": "hi", "message": "there"},
        resource_type="users",
        resource_id=1,
        id="evt-1",
    )

    payload = event.to_dict()

    assert payload["event"] == "notification"
    assert payload["id"] == "evt-1"
    assert payload["data"]["title"] == "hi"
    assert payload["data"]["message"] == "there"
    assert payload["data"]["resource_type"] == "users"
    assert payload["data"]["resource_id"] == 1
    assert "timestamp" in payload["data"]


@pytest.mark.asyncio
async def test_publish_toast_event() -> None:
    hub = AdminEventHub()
    subscription, task = await start_subscription(
        hub, event_types=[AdminEventType.TOAST]
    )

    delivered = await hub.publish_toast(
        message="done", variant="success", duration=3000
    )
    event = await task

    assert event.event_type == AdminEventType.TOAST
    assert event.data["message"] == "done"
    assert event.data["variant"] == "success"
    assert event.data["duration"] == 3000

    await close_subscription(subscription, task)
