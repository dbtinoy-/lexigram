"""Tests for DefaultMiddlewareStack.

Covers:
- ``DefaultMiddlewareStack.build()`` always includes ``DIScopeMiddleware``
- Extra middlewares are prepended before the DI-scope entry
- The class is importable from both ``lexigram.web.middleware`` and
  ``lexigram.web``
- ``WebMiddlewareManager.build_native_stack`` produces an equivalent result
"""

from __future__ import annotations

import pytest
from starlette.middleware import Middleware as StarletteMiddleware

# ---------------------------------------------------------------------------
# Test 1 — importable from lexigram.web.middleware and lexigram.web
# ---------------------------------------------------------------------------


def test_default_middleware_stack_importable_from_middleware_package() -> None:
    """``DefaultMiddlewareStack`` is exported from ``lexigram.web.middleware``."""
    from lexigram.web.middleware import DefaultMiddlewareStack  # noqa: F401

    assert DefaultMiddlewareStack is not None


def test_default_middleware_stack_importable_from_lexigram_web() -> None:
    """``DefaultMiddlewareStack`` is importable from the root ``lexigram.web`` package."""
    from lexigram.web import DefaultMiddlewareStack  # noqa: F401

    assert DefaultMiddlewareStack is not None


# ---------------------------------------------------------------------------
# Test 2 — build() returns a list of StarletteMiddleware with DIScopeMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_stack_includes_di_scope_middleware() -> None:
    """``build()`` always includes ``DIScopeMiddleware`` as a Starlette entry.

    Even with an empty ``extra_middlewares`` list the stack must contain at
    least the DI-scope middleware so request-scoped resolution works.
    """
    from lexigram.di.container import Container
    from lexigram.web.middleware.stack import DefaultMiddlewareStack

    container = Container()
    stack = DefaultMiddlewareStack(container=container)
    middlewares = stack.build()

    assert len(middlewares) >= 1
    assert all(isinstance(mw, StarletteMiddleware) for mw in middlewares)
    # At least one entry should wrap DIScopeMiddleware
    cls_names = [mw.cls.__name__ for mw in middlewares]
    assert "DIScopeMiddleware" in cls_names


# ---------------------------------------------------------------------------
# Test 3 — extra middlewares appear in the built list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_stack_includes_extra_middlewares() -> None:
    """User-supplied ``extra_middlewares`` are included in the built stack.

    The stack count grows by one for each extra middleware supplied.
    Lexigram middleware instances are wrapped as ``_LexigramMiddlewareAdapter``
    Starlette entries — the adapted wrapper class name is not the original class
    name.
    """
    from lexigram.di.container import Container
    from lexigram.web.middleware.stack import DefaultMiddlewareStack
    from lexigram.web.middleware.timing import TimingMiddleware

    container = Container()

    # Baseline — no extra middleware
    base_stack = DefaultMiddlewareStack(container=container)
    base_count = len(base_stack.build())

    # Stack with one extra Lexigram middleware
    timing_mw = TimingMiddleware(app=None)  # type: ignore[arg-type]
    extended_stack = DefaultMiddlewareStack(
        container=container,
        extra_middlewares=[timing_mw],
    )
    extended = extended_stack.build()

    # One extra entry should appear
    assert len(extended) == base_count + 1
    # Lexigram middlewares are wrapped by _LexigramMiddlewareAdapter
    cls_names = [mw.cls.__name__ for mw in extended]
    assert "_LexigramMiddlewareAdapter" in cls_names
    assert "DIScopeMiddleware" in cls_names


# ---------------------------------------------------------------------------
# Test 4 — WebMiddlewareManager delegates to DefaultMiddlewareStack (DRY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_middleware_manager_delegates_to_default_stack() -> None:
    """``WebMiddlewareManager.build_native_stack`` delegates to ``DefaultMiddlewareStack``.

    The list produced by the manager must match what ``DefaultMiddlewareStack``
    would produce independently for the same inputs (DRY guarantee).
    """
    from lexigram.di.container import Container
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.middleware.manager import WebMiddlewareManager
    from lexigram.web.middleware.stack import DefaultMiddlewareStack

    container = Container()
    provider = WebProvider(web_config=WebConfig())
    manager = WebMiddlewareManager(provider)

    manager_result = manager.build_native_stack(container)
    stack_result = DefaultMiddlewareStack(
        container=container,
        extra_middlewares=list(provider.middleware),
    ).build()

    assert len(manager_result) == len(stack_result)
    assert [mw.cls for mw in manager_result] == [mw.cls for mw in stack_result]
