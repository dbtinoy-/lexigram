"""Tests for action lifecycle hooks in ActionExecutor.

Covers action-level (handler) and resource-level hooks: data amendment,
abort-on-Err, after hooks, and failure hooks.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.exceptions import AdminError
from lexigram.admin.services.action_executor import ActionExecutor
from lexigram.admin.services.action_registry import (
    ActionConfig,
    ActionContext,
    ActionRegistry,
    FunctionActionHandler,
)
from lexigram.result import Err, Ok, Result


class RecordingHook:
    """Test hook recording calls with configurable behavior."""

    def __init__(self) -> None:
        self.before_calls: list[tuple[Any, dict[str, Any]]] = []
        self.after_calls: list[tuple[Any, Any]] = []
        self.failure_calls: list[tuple[Any, Exception]] = []
        self.amendments: dict[str, Any] | None = None
        self.abort_error: AdminError | None = None

    async def before(
        self, record: Any, data: dict[str, Any]
    ) -> Result[dict[str, Any], AdminError]:
        self.before_calls.append((record, dict(data)))
        if self.abort_error is not None:
            return Err(self.abort_error)
        return Ok(self.amendments if self.amendments is not None else {})

    async def after(self, record: Any, result: Any) -> None:
        self.after_calls.append((record, result))

    async def on_failure(self, record: Any, error: Exception) -> None:
        self.failure_calls.append((record, error))


def build_executor(
    seen: list[dict[str, Any]],
    handler: FunctionActionHandler | None = None,
    resource_resolver: Any | None = None,
) -> tuple[ActionExecutor, FunctionActionHandler]:
    """Build an executor with a registered ``notify`` action on ``users``."""

    async def execute(ctx: ActionContext) -> dict[str, Any]:
        seen.append(dict(ctx.parameters))
        return {"notified": True}

    if handler is None:
        handler = FunctionActionHandler(execute)
    registry = ActionRegistry()
    registry.register(
        "users",
        ActionConfig(name="notify", label="Notify", description=""),
        handler,
    )
    executor = ActionExecutor(registry, resource_resolver=resource_resolver)
    return executor, handler


def make_context(**overrides: Any) -> ActionContext:
    params = {"payload": "original"}
    params.update(overrides.pop("parameters", {}))
    return ActionContext(
        user=None,
        resource_name="users",
        action_name="notify",
        parameters=params,
        **overrides,
    )


class TestBeforeHooks:
    async def test_before_hook_can_modify_data(self) -> None:
        hook = RecordingHook()
        hook.amendments = {"note": "added-by-hook"}
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(before=[hook])

        result = await executor.execute(make_context())

        assert result.is_ok()
        assert hook.before_calls[0][1] == {"payload": "original"}
        assert seen[-1]["note"] == "added-by-hook"

    async def test_before_hook_aborts_action(self) -> None:
        hook = RecordingHook()
        hook.abort_error = AdminError(message="blocked by hook")
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(before=[hook], failure=[hook])

        result = await executor.execute(make_context())

        assert result.is_err()
        assert result.unwrap_err().message == "blocked by hook"
        assert seen == []

    async def test_multiple_before_hooks_run_in_order(self) -> None:
        first = RecordingHook()
        second = RecordingHook()
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(before=[first, second])

        result = await executor.execute(make_context())

        assert result.is_ok()
        assert first.before_calls[0][1] == {"payload": "original"}
        assert len(second.before_calls) == 1


class TestAfterHooks:
    async def test_after_hook_receives_result(self) -> None:
        hook = RecordingHook()
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(after=[hook])

        result = await executor.execute(make_context())

        assert result.is_ok()
        assert len(hook.after_calls) == 1
        assert hook.after_calls[0][1].data == {"notified": True}

    async def test_after_hook_not_called_on_failure(self) -> None:
        hook = RecordingHook()
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(after=[hook])
        handler.before_hooks = []  # type: ignore[misc]

        async def boom(ctx: ActionContext) -> dict[str, Any]:
            raise ValueError("boom")

        handler.func = boom  # type: ignore[assignment]

        result = await executor.execute(make_context())

        assert result.is_err()
        assert hook.after_calls == []


class TestFailureHooks:
    async def test_failure_hook_called_when_before_returns_err(self) -> None:
        hook = RecordingHook()
        hook.abort_error = AdminError(message="blocked")
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(before=[hook], failure=[hook])

        result = await executor.execute(make_context())

        assert result.is_err()
        assert len(hook.failure_calls) == 1
        assert hook.failure_calls[0][1].message == "blocked"
        assert hook.after_calls == []

    async def test_failure_hook_called_on_action_exception(self) -> None:
        hook = RecordingHook()
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(failure=[hook])

        async def boom(ctx: ActionContext) -> dict[str, Any]:
            raise ValueError("boom")

        handler.func = boom  # type: ignore[assignment]

        result = await executor.execute(make_context())

        assert result.is_err()
        assert result.unwrap_err().message == "boom"
        assert len(hook.failure_calls) == 1
        assert isinstance(hook.failure_calls[0][1], ValueError)


class TestHookRegistrationLevels:
    async def test_action_level_hooks_registered_on_handler(self) -> None:
        hook = RecordingHook()
        seen: list[dict[str, Any]] = []
        executor, handler = build_executor(seen)
        handler.register_hooks(before=[hook], after=[hook], failure=[hook])

        result = await executor.execute(make_context())

        assert result.is_ok()
        assert len(hook.before_calls) == 1
        assert len(hook.after_calls) == 1
        assert hook.failure_calls == []

    async def test_resource_level_hooks_via_get_action_hooks(self) -> None:
        hook = RecordingHook()

        class HookedResource:
            @classmethod
            def get_action_hooks(cls, action_name: str) -> list[Any]:
                if action_name == "notify":
                    return [hook]
                return []

        seen: list[dict[str, Any]] = []
        executor, _ = build_executor(
            seen, resource_resolver=lambda _name: HookedResource
        )

        result = await executor.execute(make_context())

        assert result.is_ok()
        assert len(hook.before_calls) == 1
        assert len(hook.after_calls) == 1

    async def test_resource_level_hook_aborts_action(self) -> None:
        hook = RecordingHook()
        hook.abort_error = AdminError(message="resource policy")

        class HookedResource:
            @classmethod
            def get_action_hooks(cls, action_name: str) -> list[Any]:
                return [hook]

        seen: list[dict[str, Any]] = []
        executor, _ = build_executor(
            seen, resource_resolver=lambda _name: HookedResource
        )

        result = await executor.execute(make_context())

        assert result.is_err()
        assert result.unwrap_err().message == "resource policy"
        assert seen == []
