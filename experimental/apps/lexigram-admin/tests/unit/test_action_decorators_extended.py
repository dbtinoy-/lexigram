"""Extended tests for actions/decorators.py — shared action decorator utilities."""

from __future__ import annotations

import asyncio
import time

import pytest

from lexigram.admin.actions.decorators import (
    debounce,
    requires_confirmation,
    with_error_handling,
    with_loading_indicator,
)


class TestRequiresConfirmation:
    """Tests for requires_confirmation decorator."""

    @pytest.mark.asyncio
    async def test_calls_wrapped_function(self) -> None:
        called = []

        @requires_confirmation(message="Sure?", title="Confirm")
        async def action(*args, **kwargs):
            called.append((args, kwargs))
            return "done"

        result = await action("arg1", key="val")
        assert result == "done"
        assert called == [(("arg1",), {"key": "val"})]

    @pytest.mark.asyncio
    async def test_default_message(self) -> None:
        @requires_confirmation()
        async def action():
            return "ok"

        result = await action()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        @requires_confirmation(message="Delete?")
        async def delete_item():
            """Delete an item."""
            return "deleted"

        assert delete_item.__name__ == "delete_item"
        assert "Delete an item" in delete_item.__doc__


class TestWithLoadingIndicator:
    """Tests for with_loading_indicator decorator."""

    @pytest.mark.asyncio
    async def test_calls_wrapped_function(self) -> None:
        @with_loading_indicator("Working...")
        async def action():
            return "result"

        result = await action()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_default_loading_text(self) -> None:
        @with_loading_indicator()
        async def action():
            return "ok"

        result = await action()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_returns_value_on_success(self) -> None:
        @with_loading_indicator()
        async def action():
            return {"id": 1, "name": "Test"}

        result = await action()
        assert result == {"id": 1, "name": "Test"}

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        @with_loading_indicator("Loading...")
        async def my_action():
            """My action docstring."""
            pass

        assert my_action.__name__ == "my_action"


class TestWithErrorHandling:
    """Tests for with_error_handling decorator."""

    @pytest.mark.asyncio
    async def test_calls_wrapped_function(self) -> None:
        @with_error_handling()
        async def action():
            return "ok"

        result = await action()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_custom_error_message(self) -> None:
        @with_error_handling(error_message="Custom error")
        async def action():
            return "ok"

        result = await action()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        @with_error_handling()
        async def my_action():
            """My action."""
            pass

        assert my_action.__name__ == "my_action"


class TestDebounce:
    """Tests for debounce decorator."""

    @pytest.mark.asyncio
    async def test_calls_function_immediately_first_time(self) -> None:
        called = []

        @debounce(delay=0.01)
        async def action():
            called.append(1)
            return len(called)

        result = await action()
        assert result == 1
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_allows_second_call_after_delay(self) -> None:
        called = []

        @debounce(delay=0.01)
        async def action():
            called.append(1)
            return len(called)

        await action()
        await asyncio.sleep(0.02)  # Wait longer than debounce delay
        result = await action()
        assert result == 2
        assert len(called) == 2

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        @debounce(delay=0.1)
        async def my_slow_action():
            """Slow action."""
            pass

        assert my_slow_action.__name__ == "my_slow_action"

    @pytest.mark.asyncio
    async def test_default_delay(self) -> None:
        @debounce()
        async def action():
            return "ok"

        result = await action()
        assert result == "ok"
