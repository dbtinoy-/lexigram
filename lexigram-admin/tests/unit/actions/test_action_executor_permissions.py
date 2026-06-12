"""Tests for per-action permission enforcement in ActionExecutor.

Covers the live per-action dispatch path: ``execute`` denying/allowing
based on ``ActionConfig.permission`` via the authorizer, and
``get_available_actions`` filtering by user permissions.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.services.action_executor import ActionExecutor
from lexigram.admin.services.action_registry import (
    ActionConfig,
    ActionContext,
    ActionRegistry,
    FunctionActionHandler,
)


class RecordingAuthorizer:
    """Fake authorizer recording calls with a configurable decision."""

    def __init__(self, decision: bool) -> None:
        self.decision = decision
        self.calls: list[tuple[Any, str, str]] = []

    async def can_execute_action(
        self,
        user: Any,
        resource: str,
        action: str,
        record: Any | None = None,
    ) -> bool:
        self.calls.append((user, resource, action))
        return self.decision


def build_handler(seen: list[dict[str, Any]]) -> FunctionActionHandler:
    async def execute(ctx: ActionContext) -> dict[str, Any]:
        seen.append({"action": ctx.action_name})
        return {"ok": True}

    return FunctionActionHandler(execute)


def make_context(resource: str = "relay", action: str = "bill") -> ActionContext:
    return ActionContext(user=None, resource_name=resource, action_name=action)


async def test_execute_denies_when_action_declares_permission_and_user_lacks_it() -> (
    None
):
    seen: list[dict[str, Any]] = []
    registry = ActionRegistry()
    registry.register(
        "relay",
        ActionConfig(name="bill", label="Bill", permission="relay.billing"),
        build_handler(seen),
    )
    authorizer = RecordingAuthorizer(decision=False)
    executor = ActionExecutor(registry, authorizer=authorizer)

    result = await executor.execute(make_context())

    assert result.is_err()
    assert isinstance(result.unwrap_err(), PermissionDeniedError)
    assert seen == []


async def test_execute_allows_when_action_has_no_permission() -> None:
    seen: list[dict[str, Any]] = []
    registry = ActionRegistry()
    registry.register(
        "relay",
        ActionConfig(name="ping", label="Ping"),
        build_handler(seen),
    )
    authorizer = RecordingAuthorizer(decision=True)
    executor = ActionExecutor(registry, authorizer=authorizer)

    result = await executor.execute(make_context(action="ping"))

    assert result.is_ok()
    assert seen == [{"action": "ping"}]
    assert authorizer.calls == []


async def test_execute_allows_when_user_has_declared_permission() -> None:
    seen: list[dict[str, Any]] = []
    registry = ActionRegistry()
    registry.register(
        "relay",
        ActionConfig(name="bill", label="Bill", permission="relay.billing"),
        build_handler(seen),
    )
    authorizer = RecordingAuthorizer(decision=True)
    executor = ActionExecutor(registry, authorizer=authorizer)

    result = await executor.execute(make_context())

    assert result.is_ok()
    assert seen == [{"action": "bill"}]
    assert authorizer.calls == [(None, "relay", "bill")]


def test_get_available_actions_filters_by_permission() -> None:
    registry = ActionRegistry()
    for name, permission in [
        ("deactivate", "users.deactivate"),
        ("delete", "users.delete"),
        ("export", None),
    ]:
        registry.register(
            "users",
            ActionConfig(name=name, label=name.title(), permission=permission),
            build_handler([]),
        )
    executor = ActionExecutor(registry)

    available = executor.get_available_actions(
        "users", user_permissions={"users.deactivate"}
    )

    names = [a.name for a in available]
    assert "deactivate" in names
    assert "export" in names
    assert "delete" not in names
