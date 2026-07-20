"""Tests for the reactive activity widget in the core contributor."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.admin.realtime.sse import AdminEvent, AdminEventType
from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub
from lexigram.contracts.admin import EmptyContent, TableContent, WidgetParams


async def test_activity_widget_definition_is_live() -> None:
    """The activity widget declares itself live so the dashboard drops polling for it."""
    contributor = CoreAdminContributor()
    widgets = {w.name: w for w in contributor.get_dashboard_widgets()}
    assert widgets["activity"].live_resource_types == ("*",)


class StubResolver:
    """Minimal container-resolver stand-in returning the hub."""

    def __init__(self, hub: SubjectAdminEventHub) -> None:
        self._hub = hub

    async def resolve(
        self, service_type: Any, *, bypass_visibility: bool = False
    ) -> Any:
        return self._hub

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("not expected to be called in this test")

    def create_scope(self) -> Any:
        return None

    def has(self, service_type: Any) -> bool:
        return False

    async def resolve_optional(self, service_type: Any) -> Any | None:
        return None

    async def resolve_all(self, service_type: Any) -> list[Any]:
        return []


async def test_activity_widget_renders_reactive_table_when_hub_resolvable() -> None:
    hub = SubjectAdminEventHub()
    contributor = CoreAdminContributor()
    resolver = StubResolver(hub)

    # Warm the lazy resolution so the background tail subscribes before
    # the events are published (the subject is hot — no replay).
    result = await contributor.render_widget("activity", WidgetParams(), resolver)
    assert result.is_ok()
    assert isinstance(result.unwrap().content, EmptyContent)
    await asyncio.sleep(0)  # let the background tail subscribe to the hub

    await hub.publish(
        AdminEvent(
            event_type=AdminEventType.RESOURCE_UPDATED,
            data={"op": "update"},
            resource_type="users",
            resource_id=1,
        )
    )
    await hub.publish(
        AdminEvent(
            event_type=AdminEventType.NOTIFICATION,
            data={"title": "hi"},
            resource_type="",
            resource_id=None,
        )
    )
    await asyncio.sleep(0.02)

    result = await contributor.render_widget("activity", WidgetParams(), resolver)
    assert result.is_ok()
    content = result.unwrap().content
    assert isinstance(content, TableContent)
    assert len(content.rows) == 2
    assert content.rows[0][0].text == "resource.updated"
    assert content.rows[1][0].text == "notification"


async def test_activity_widget_ignores_targeted_events() -> None:
    hub = SubjectAdminEventHub()
    contributor = CoreAdminContributor(hub=hub)
    await asyncio.sleep(0)  # let the background tail subscribe to the hub
    await hub.publish(
        AdminEvent(
            event_type="resource.deleted",
            data={},
            resource_type="users",
            resource_id=99,
        ),
        target_users=["admin-1"],
    )
    await asyncio.sleep(0)
    result = await contributor.render_widget("activity", WidgetParams())
    assert result.is_ok()
    assert isinstance(result.unwrap().content, EmptyContent)


async def test_activity_widget_falls_back_to_empty_content() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("activity", WidgetParams())
    assert result.is_ok()
    assert isinstance(result.unwrap().content, EmptyContent)


__all__ = [
    "test_activity_widget_falls_back_to_empty_content",
    "test_activity_widget_ignores_targeted_events",
    "test_activity_widget_renders_reactive_table_when_hub_resolvable",
]
