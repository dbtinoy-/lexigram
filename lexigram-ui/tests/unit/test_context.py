"""Tests for UI context management."""

import dataclasses

import pytest

from lexigram.ui.core.context import (
    UIContext,
    get_ui_context,
    reset_ui_context,
    set_ui_context,
)


class TestUIContext:
    """Tests for UIContext dataclass."""

    def test_default_context(self) -> None:
        """Test default context values."""
        ctx = UIContext()
        assert ctx.theme == "default"
        assert ctx.locale == "en"
        assert ctx.user is None
        assert ctx.extra == {}

    def test_context_with_values(self) -> None:
        """Test context with custom values."""
        ctx = UIContext(theme="dark", locale="fr-FR", user={"id": "user-1"})
        assert ctx.theme == "dark"
        assert ctx.locale == "fr-FR"
        assert ctx.user == {"id": "user-1"}

    def test_context_with_extra(self) -> None:
        """Test context with extra data."""
        ctx = UIContext(extra={"key": "value", "count": 42})
        assert ctx.extra["key"] == "value"
        assert ctx.extra["count"] == 42

    def test_context_immutable(self) -> None:
        """Test that context is frozen/immutable."""
        ctx = UIContext(theme="dark")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.theme = "light"

    def test_context_repr(self) -> None:
        """Test context repr."""
        ctx = UIContext(theme="dark", locale="en")
        repr_str = repr(ctx)
        assert "theme='dark'" in repr_str
        assert "locale='en'" in repr_str

    def test_context_repr_with_user(self) -> None:
        """Test context repr with user."""
        user = type("User", (), {"id": "user-123"})()
        ctx = UIContext(user=user)
        repr_str = repr(ctx)
        assert "user=" in repr_str


class TestUIContextFunctions:
    """Tests for context management functions."""

    def test_get_ui_context_no_context(self) -> None:
        """Test getting context when none is set."""
        # Context should be None by default
        ctx = get_ui_context()
        assert ctx is None

    def test_set_and_get_context(self) -> None:
        """Test setting and getting context."""
        ctx = UIContext(theme="dark", locale="fr")
        token = set_ui_context(ctx)
        try:
            result = get_ui_context()
            assert result is ctx
            assert result.theme == "dark"
            assert result.locale == "fr"
        finally:
            reset_ui_context(token)

    def test_reset_context(self) -> None:
        """Test resetting context restores previous state."""
        ctx1 = UIContext(theme="light")
        ctx2 = UIContext(theme="dark")

        token1 = set_ui_context(ctx1)
        assert get_ui_context() == ctx1

        token2 = set_ui_context(ctx2)
        assert get_ui_context() == ctx2

        reset_ui_context(token2)
        assert get_ui_context() == ctx1

        reset_ui_context(token1)
        assert get_ui_context() is None

    def test_context_isolation(self) -> None:
        """Test that contexts are isolated per task."""
        import asyncio

        results: list[str] = []

        async def task1():
            ctx = UIContext(theme="dark")
            token = set_ui_context(ctx)
            try:
                await asyncio.sleep(0.01)
                result = get_ui_context()
                results.append(result.theme if result else "none")
            finally:
                reset_ui_context(token)

        async def task2():
            ctx = UIContext(theme="light")
            token = set_ui_context(ctx)
            try:
                await asyncio.sleep(0.01)
                result = get_ui_context()
                results.append(result.theme if result else "none")
            finally:
                reset_ui_context(token)

        async def main():
            await asyncio.gather(task1(), task2())

        asyncio.run(main())

        # Both tasks should see their own theme
        assert "dark" in results
        assert "light" in results
