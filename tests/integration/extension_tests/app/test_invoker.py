"""Tests for app/invoker.py - Invoker class."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.app.invoker import Invoker


async def _passthrough_invoke(fn, *a, **kw):
    """Async passthrough side-effect: calls *fn* with the given args and awaits it.

    Used to configure ``AsyncMock(side_effect=_passthrough_invoke)`` on the
    ``create_invoker().call`` mock so that tests which route through
    ``_final_handler`` get the actual function result rather than a raw
    coroutine object.  Must be ``async def`` because Python 3.13's
    ``AsyncMock._execute_mock_call`` only awaits the ``side_effect`` result
    when ``iscoroutinefunction(effect)`` is True.
    """
    return await fn(*a, **kw)


class TestInvokerInit:
    """Tests for Invoker initialization."""

    def test_init(self) -> None:
        """Test Invoker initialization."""
        mock_container = MagicMock()
        mock_middleware = MagicMock()

        invoker = Invoker(mock_container, mock_middleware)
        assert invoker._container is mock_container
        assert invoker._middleware is mock_middleware


class TestInvokerInvoke:
    """Tests for Invoker.invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_calls_middleware_execute(self) -> None:
        """Test invoke calls middleware.execute."""
        mock_container = MagicMock()
        mock_middleware = MagicMock()
        mock_middleware.execute = AsyncMock(return_value="result")

        invoker = Invoker(mock_container, mock_middleware)

        async def my_func():
            return "inner_result"

        result = await invoker.invoke(my_func)

        assert result == "result"
        mock_middleware.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_passes_args(self) -> None:
        """Test invoke passes arguments to function."""
        mock_container = MagicMock()
        # create_invoker() must return an invoker whose .call is awaitable and
        # delegates to the actual function so the middleware chain completes.
        mock_container.create_invoker.return_value.call = AsyncMock(
            side_effect=_passthrough_invoke
        )
        mock_middleware = AsyncMock()

        async def handler(ctx=None):
            return ctx.get("args")

        call_args = {}

        async def capture_execute(ctx, final_handler):
            call_args["ctx"] = ctx
            call_args["func"] = ctx.get("func")
            call_args["args"] = ctx.get("args")
            call_args["kwargs"] = ctx.get("kwargs")
            return await final_handler(ctx)

        mock_middleware.execute = AsyncMock(side_effect=capture_execute)

        invoker = Invoker(mock_container, mock_middleware)

        async def my_func(a, b, c=None):
            return (a, b, c)

        result = await invoker.invoke(my_func, 1, 2, c=3)

        assert call_args["args"] == (1, 2)
        assert call_args["kwargs"] == {"c": 3}

    @pytest.mark.asyncio
    async def test_invoke_returns_handler_result(self) -> None:
        """Test invoke returns the handler's result."""
        mock_container = MagicMock()
        # create_invoker() must return an invoker whose .call is awaitable and
        # delegates to the actual function so the middleware chain completes.
        mock_container.create_invoker.return_value.call = AsyncMock(
            side_effect=_passthrough_invoke
        )

        async def capture_execute(ctx, final_handler):
            return await final_handler(ctx)

        mock_middleware = AsyncMock()
        mock_middleware.execute = AsyncMock(side_effect=capture_execute)

        invoker = Invoker(mock_container, mock_middleware)

        async def my_func():
            return "expected_result"

        result = await invoker.invoke(my_func)
        assert result == "expected_result"


class TestInvokerContext:
    """Tests for context passed through invoke."""

    @pytest.mark.asyncio
    async def test_invoke_sets_func_in_context(self) -> None:
        """Test that func is set in context."""
        mock_container = MagicMock()
        # create_invoker() must return an invoker whose .call is awaitable and
        # delegates to the actual function so the middleware chain completes.
        mock_container.create_invoker.return_value.call = AsyncMock(
            side_effect=_passthrough_invoke
        )
        captured_ctx = {}

        async def capture_execute(ctx, final_handler):
            captured_ctx.update(ctx)
            return await final_handler(ctx)

        mock_middleware = AsyncMock()
        mock_middleware.execute = AsyncMock(side_effect=capture_execute)

        invoker = Invoker(mock_container, mock_middleware)

        async def my_func():
            pass

        await invoker.invoke(my_func)

        assert "func" in captured_ctx
        assert captured_ctx["func"] is my_func
