"""Tests for audit decorators."""

from __future__ import annotations

import pytest

from lexigram.audit.decorators import audited


class TestAuditedDecorator:
    """Tests for @audited decorator."""

    def test_decorator_sets_attributes(self) -> None:
        @audited("user.login")
        async def login() -> str:
            return "success"

        assert hasattr(login, "__audited__")
        assert login.__audited__ is True
        assert login.__audit_action__ == "user.login"
        assert login.__audit_resource_type__ == ""
        assert login.__audit_severity__ == "medium"

    def test_decorator_with_resource_type(self) -> None:
        @audited("user.update", resource_type="User")
        async def update_user(user_id: str) -> dict:
            return {"id": user_id}

        assert update_user.__audit_action__ == "user.update"
        assert update_user.__audit_resource_type__ == "User"

    def test_decorator_with_custom_severity(self) -> None:
        @audited("system.delete", severity="critical")
        async def delete_resource(resource_id: str) -> None:
            pass

        assert delete_resource.__audit_severity__ == "critical"

    def test_decorator_preserves_function_name(self) -> None:
        @audited("test.action")
        async def my_function() -> None:
            pass

        assert my_function.__name__ == "my_function"

    def test_decorator_preserves_function_docstring(self) -> None:
        @audited("test.action")
        async def documented_function() -> str:
            """This is the docstring."""
            return "doc"

        assert documented_function.__doc__ == "This is the docstring."

    def test_decorator_can_be_applied_twice(self) -> None:
        @audited("first.action")
        @audited("second.action")
        async def nested() -> None:
            pass

        # Decorators apply from bottom up, so first.action overwrites second.action
        assert nested.__audit_action__ == "first.action"

    @pytest.mark.asyncio
    async def test_decorated_function_executes(self) -> None:
        @audited("test.action")
        async def do_something() -> str:
            return "executed"

        result = await do_something()
        assert result == "executed"

    @pytest.mark.asyncio
    async def test_decorated_function_passes_args(self) -> None:
        @audited("test.action")
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_decorated_function_passes_kwargs(self) -> None:
        @audited("test.action")
        async def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result = await greet("World", greeting="Hi")
        assert result == "Hi, World!"

    def test_decorator_all_attributes_set(self) -> None:
        @audited(
            "admin.permission.change",
            resource_type="Permission",
            severity="high",
        )
        async def change_permission() -> None:
            pass

        assert change_permission.__audited__ is True
        assert change_permission.__audit_action__ == "admin.permission.change"
        assert change_permission.__audit_resource_type__ == "Permission"
        assert change_permission.__audit_severity__ == "high"


# Helper to test decorator without async
def test_sync_function_can_be_decorated() -> None:
    @audited("sync.action")
    def sync_function() -> str:
        return "sync"

    assert sync_function.__audit_action__ == "sync.action"