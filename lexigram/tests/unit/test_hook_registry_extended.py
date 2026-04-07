"""Comprehensive additional tests for HookRegistry system."""

from __future__ import annotations

import pytest

from lexigram.contracts.core.hooks import HookPriority
from lexigram.hooks import HookRegistry


class TestHookRegistryIntrospection:
    """Tests for introspection methods."""

    def test_action_names_returns_registered_hook_names(self) -> None:
        registry = HookRegistry()
        registry.register_action("init", lambda **_: None)
        registry.register_action("init", lambda **_: None)  # same hook
        registry.register_action("shutdown", lambda **_: None)

        names = registry.action_names()
        assert "init" in names
        assert "shutdown" in names
        assert len(names) == 2

    def test_filter_names_returns_registered_hook_names(self) -> None:
        registry = HookRegistry()
        registry.register_filter("sanitize", lambda x, **_: x)
        registry.register_filter("transform", lambda x, **_: x)

        names = registry.filter_names()
        assert "sanitize" in names
        assert "transform" in names

    def test_action_names_excludes_empty_hooks(self) -> None:
        registry = HookRegistry()
        registry.register_action("empty", lambda **_: None)
        entry = next(iter(registry._actions["empty"]))
        registry.unregister_action("empty", entry.handler)

        names = registry.action_names()
        assert "empty" not in names

    def test_filter_names_excludes_empty_hooks(self) -> None:
        registry = HookRegistry()
        registry.register_filter("empty", lambda x, **_: x)
        entry = next(iter(registry._filters["empty"]))
        registry.unregister_filter("empty", entry.handler)

        names = registry.filter_names()
        assert "empty" not in names


class TestHookRegistryUnregistration:
    """Tests for unregistration methods."""

    def test_unregister_filter_returns_true_when_found(self) -> None:
        registry = HookRegistry()

        def handler(value: int, **_: object) -> int:
            return value

        registry.register_filter("transform", handler)
        result = registry.unregister_filter("transform", handler)
        assert result is True

    def test_unregister_filter_returns_false_when_not_found(self) -> None:
        registry = HookRegistry()

        def handler(value: int, **_: object) -> int:
            return value

        registry.register_filter("transform", handler)
        result = registry.unregister_filter("transform", lambda x, **_: x)
        assert result is False

    def test_unregister_filter_removes_from_list(self) -> None:
        registry = HookRegistry()

        def h1(value: int, **_: object) -> int:
            return value

        def h2(value: int, **_: object) -> int:
            return value

        registry.register_filter("transform", h1)
        registry.register_filter("transform", h2)

        registry.unregister_filter("transform", h1)
        entries = registry._filters.get("transform", [])
        assert len(entries) == 1
        assert entries[0].handler is h2

    def test_unregister_filter_nonexistent_hook_returns_false(self) -> None:
        registry = HookRegistry()
        result = registry.unregister_filter("nonexistent", lambda x, **_: x)
        assert result is False


class TestSyncHandlers:
    """Tests for synchronous (non-async) handlers."""

    @pytest.mark.asyncio
    async def test_sync_action_handler_is_called(self) -> None:
        registry = HookRegistry()
        called = False

        def handler(**_: object) -> None:
            nonlocal called
            called = True

        registry.register_action("init", handler)
        await registry.call_action("init")
        assert called is True

    @pytest.mark.asyncio
    async def test_sync_filter_handler_transforms_value(self) -> None:
        registry = HookRegistry()

        def double(value: int, **_: object) -> int:
            return value * 2

        registry.register_filter("transform", double)
        result = await registry.apply_filter("transform", 5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_mixed_sync_and_async_handlers(self) -> None:
        registry = HookRegistry()
        results: list[int] = []

        def sync_add10(value: int, **_: object) -> int:
            return value + 10

        async def async_mul2(value: int, **_: object) -> int:
            return value * 2

        registry.register_filter("transform", sync_add10, priority=100)
        registry.register_filter("transform", async_mul2, priority=200)

        result = await registry.apply_filter("transform", 3)
        assert result == 26  # (3 + 10) * 2


class TestComplexPriorityScenarios:
    """Tests for complex priority ordering scenarios."""

    @pytest.mark.asyncio
    async def test_many_handlers_priority_ordering(self) -> None:
        registry = HookRegistry()
        order: list[int] = []

        handlers = [
            (lambda **_: order.append(10), 10),
            (lambda **_: order.append(300), 300),
            (lambda **_: order.append(50), 50),
            (lambda **_: order.append(200), 200),
            (lambda **_: order.append(0), 0),
            (lambda **_: order.append(150), 150),
            (lambda **_: order.append(100), 100),
            (lambda **_: order.append(250), 250),
        ]

        for handler, priority in handlers:
            registry.register_action("test", handler, priority=priority)

        await registry.call_action("test")

        expected = [0, 10, 50, 100, 150, 200, 250, 300]
        assert order == expected

    @pytest.mark.asyncio
    async def test_same_priority_maintains_insertion_order(self) -> None:
        registry = HookRegistry()
        order: list[str] = []

        def make_handler(name: str):
            def handler(**_: object) -> None:
                order.append(name)
            return handler

        registry.register_action("test", make_handler("a"), priority=100)
        registry.register_action("test", make_handler("b"), priority=100)
        registry.register_action("test", make_handler("c"), priority=100)

        await registry.call_action("test")
        assert order == ["a", "b", "c"]


class TestConcurrentAccess:
    """Tests for thread-safety under concurrent access."""

    def test_concurrent_registration_is_thread_safe(self) -> None:
        import threading

        registry = HookRegistry()
        errors: list[Exception] = []

        def register_handlers() -> None:
            try:
                for i in range(50):
                    registry.register_action("concurrent", lambda **_: None, priority=i)
                    registry.register_filter("concurrent", lambda x, **_: x, priority=i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_handlers) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.has_action("concurrent")

    @pytest.mark.asyncio
    async def test_read_during_write(self) -> None:
        import asyncio

        registry = HookRegistry()
        errors: list[Exception] = []

        async def reader() -> None:
            for _ in range(100):
                try:
                    _ = registry.has_action("test")
                    _ = registry.has_filter("test")
                    _ = registry.action_names()
                except Exception as e:
                    errors.append(e)
                await asyncio.sleep(0)

        async def writer() -> None:
            for i in range(100):
                try:
                    registry.register_action("test", lambda **_: None, priority=i)
                    registry.register_filter("test", lambda x, **_: x, priority=i)
                except Exception as e:
                    errors.append(e)
                await asyncio.sleep(0)

        await asyncio.gather(reader(), writer())

        assert len(errors) == 0  # No exceptions should be raised


class TestReprAndDebugging:
    """Tests for __repr__ output."""

    def test_repr_shows_name(self) -> None:
        registry = HookRegistry("my-app")
        assert "my-app" in repr(registry)

    def test_repr_shows_actions(self) -> None:
        registry = HookRegistry()
        registry.register_action("init", lambda **_: None)
        registry.register_action("init", lambda **_: None)  # 2 handlers

        r = repr(registry)
        assert "init" in r
        assert "2 handlers" in r

    def test_repr_shows_filters(self) -> None:
        registry = HookRegistry()
        registry.register_filter("sanitize", lambda x, **_: x)

        r = repr(registry)
        assert "sanitize" in r

    def test_repr_shows_both_actions_and_filters(self) -> None:
        registry = HookRegistry()
        registry.register_action("action_hook", lambda **_: None)
        registry.register_filter("filter_hook", lambda x, **_: x)

        r = repr(registry)
        assert "actions=" in r
        assert "filters=" in r


class TestDecoratorWithNonDefaultPriority:
    """Tests for decorator with custom priority values."""

    @pytest.mark.asyncio
    async def test_decorator_with_explicit_priority(self) -> None:
        registry = HookRegistry()
        order: list[str] = []

        @registry.action("test", priority=HookPriority.LATE)
        async def late(**_: object) -> None:
            order.append("late")

        @registry.action("test", priority=HookPriority.EARLY)
        async def early(**_: object) -> None:
            order.append("early")

        @registry.action("test", priority=HookPriority.NORMAL)
        async def normal(**_: object) -> None:
            order.append("normal")

        await registry.call_action("test")
        assert order == ["early", "normal", "late"]

    def test_decorator_with_once_flag(self) -> None:
        registry = HookRegistry()
        call_count = 0

        @registry.action("test", once=True)
        async def once_handler(**_: object) -> None:
            nonlocal call_count
            call_count += 1

        assert registry.has_action("test")

        import asyncio
        asyncio.run(registry.call_action("test"))
        asyncio.run(registry.call_action("test"))

        assert call_count == 1


class TestEmptyAndNoopScenarios:
    """Tests for edge cases with empty hooks."""

    @pytest.mark.asyncio
    async def test_call_action_with_no_kwargs(self) -> None:
        registry = HookRegistry()
        called = False

        def handler(**kwargs: object) -> None:
            nonlocal called
            called = True
            assert kwargs == {}

        registry.register_action("test", handler)
        await registry.call_action("test")
        assert called is True

    @pytest.mark.asyncio
    async def test_apply_filter_passes_kwargs(self) -> None:
        registry = HookRegistry()
        received_kwargs: dict[str, object] = {}

        def capture_kwargs(value: int, **kwargs: object) -> int:
            received_kwargs.update(kwargs)
            return value

        registry.register_filter("test", capture_kwargs)
        result = await registry.apply_filter("test", 0, user_id="user123", tenant="acme")

        assert result == 0
        assert received_kwargs == {"user_id": "user123", "tenant": "acme"}

    @pytest.mark.asyncio
    async def test_call_action_passes_all_kwargs(self) -> None:
        registry = HookRegistry()
        received_kwargs: dict[str, object] = {}

        def capture_kwargs(**kwargs: object) -> None:
            received_kwargs.update(kwargs)

        registry.register_action("test", capture_kwargs)
        await registry.call_action("test", user_id="user123", request_id="req-456")

        assert received_kwargs == {"user_id": "user123", "request_id": "req-456"}


class TestMultipleHooksIsolation:
    """Tests for multiple independent hook collections."""

    @pytest.mark.asyncio
    async def test_multiple_registries_are_independent(self) -> None:
        registry_a = HookRegistry("a")
        registry_b = HookRegistry("b")

        results_a: list[str] = []
        results_b: list[str] = []

        registry_a.register_action("test", lambda **_: results_a.append("a"))
        registry_b.register_action("test", lambda **_: results_b.append("b"))

        await registry_a.call_action("test")
        await registry_b.call_action("test")

        assert results_a == ["a"]
        assert results_b == ["b"]

    @pytest.mark.asyncio
    async def test_clear_one_registry_does_not_affect_other(self) -> None:
        registry_a = HookRegistry("a")
        registry_b = HookRegistry("b")

        registry_a.register_action("test", lambda **_: None)
        registry_b.register_action("test", lambda **_: None)

        registry_a.clear("test")

        assert registry_a.has_action("test") is False
        assert registry_b.has_action("test") is True


class TestFilterChainingComplex:
    """Tests for complex filter chaining scenarios."""

    @pytest.mark.asyncio
    async def test_filter_chain_with_none_value(self) -> None:
        registry = HookRegistry()

        async def add_suffix(value: str | None, **_: object) -> str | None:
            return f"{value}_processed" if value is not None else None

        registry.register_filter("process", add_suffix)
        result = await registry.apply_filter("process", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_filter_chain_with_complex_objects(self) -> None:
        registry = HookRegistry()

        def add_timestamp(value: dict[str, object], **_: object) -> dict[str, object]:
            value["timestamp"] = "2024-01-01"
            return value

        registry.register_filter("enrich", add_timestamp)
        result = await registry.apply_filter("enrich", {"id": 123})

        assert result["id"] == 123
        assert result["timestamp"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_filter_can_return_different_type(self) -> None:
        registry = HookRegistry()

        async def int_to_string(value: int, **_: object) -> str:
            return str(value * 2)

        registry.register_filter("convert", int_to_string)
        result = await registry.apply_filter("convert", 21)
        assert result == "42"
        assert isinstance(result, str)


class TestEdgeCaseHandlers:
    """Tests for edge case handlers."""

    @pytest.mark.asyncio
    async def test_handler_with_no_arguments(self) -> None:
        registry = HookRegistry()

        def no_args() -> None:
            pass

        registry.register_action("test", no_args)
        await registry.call_action("test")  # Should not raise

    @pytest.mark.asyncio
    async def test_handler_with_wildcard_kwargs(self) -> None:
        registry = HookRegistry()
        received: dict[str, object] = {}

        def capture_all(**kwargs: object) -> None:
            received.update(kwargs)

        registry.register_action("test", capture_all)
        await registry.call_action("test", a=1, b="two", c=[1, 2, 3])

        assert received == {"a": 1, "b": "two", "c": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_action_handler_returning_value_is_ignored(self) -> None:
        registry = HookRegistry()

        def returns_value() -> str:
            return "should be ignored"

        def records_call() -> None:
            pass

        registry.register_action("test", returns_value)
        registry.register_action("test", records_call)

        await registry.call_action("test")  # Should not raise, return value ignored


class TestHookEntryIdentity:
    """Tests for HookEntry identity handling."""

    def test_multiple_registrations_same_handler_different_entries(self) -> None:
        registry = HookRegistry()

        def handler() -> None:
            pass

        registry.register_action("test", handler)
        registry.register_action("test", handler)

        entries = registry._actions.get("test", [])
        assert len(entries) == 2
        assert entries[0].handler is entries[1].handler

    def test_unregister_only_removes_specific_entry(self) -> None:
        registry = HookRegistry()

        def handler1() -> None:
            pass

        def handler2() -> None:
            pass

        registry.register_action("test", handler1)
        registry.register_action("test", handler2)

        registry.unregister_action("test", handler1)

        entries = registry._actions.get("test", [])
        assert len(entries) == 1
        assert entries[0].handler is handler2
