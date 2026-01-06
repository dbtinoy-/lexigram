"""Tests for ShowcaseController — stateful component demonstrations."""

from __future__ import annotations

import types as _types
from unittest.mock import MagicMock

import pytest

# Stub for lexigram.admin.ui.examples.stateful_components


class _StubCounterComponent:
    def __init__(self, initial_value: int = 0) -> None:
        self.initial_value = initial_value


class _StubFormWizard:
    def __init__(self) -> None: ...


# Build stubs for modules that genuinely don't exist on disk.
# Do NOT stub modules that exist (e.g. lexigram.admin.ui.templates) — that
# breaks submodule resolution for the real package.

_stateful = _types.ModuleType("lexigram.admin.ui.examples.stateful_components")
_stateful.CounterComponent = _StubCounterComponent
_stateful.FormWizard = _StubFormWizard
_stateful.__package__ = "lexigram.admin.ui.examples"

_examples = _types.ModuleType("lexigram.admin.ui.examples")
_examples.stateful_components = _stateful
_examples.__package__ = "lexigram.admin.ui"

_page = _types.ModuleType("lexigram.admin.ui.templates.page")
_page.PageRenderer = MagicMock
_page.__package__ = "lexigram.admin.ui.templates"

_built: dict[str, object] = {}


def _setup() -> None:
    import sys

    _built.clear()
    sys.modules["lexigram.admin.ui.examples"] = _examples
    sys.modules["lexigram.admin.ui.examples.stateful_components"] = _stateful
    sys.modules["lexigram.admin.ui.templates.page"] = _page

    from lexigram.admin.controllers.showcase import ShowcaseController

    _built["ShowcaseController"] = ShowcaseController


def _teardown() -> None:
    import sys

    for key in [
        "lexigram.admin.ui.examples",
        "lexigram.admin.ui.examples.stateful_components",
        "lexigram.admin.ui.templates.page",
    ]:
        sys.modules.pop(key, None)
    _built.clear()


class TestShowcaseController:
    """Tests for ShowcaseController."""

    @pytest.fixture(autouse=True)
    def _patch_imports(self) -> None:
        _setup()
        yield
        _teardown()

    @pytest.fixture
    def renderer(self) -> MagicMock:
        r = MagicMock()
        r.render_page.return_value = "rendered"
        return r

    @pytest.fixture
    def controller(self, renderer: MagicMock) -> object:
        Cls = _built["ShowcaseController"]
        return Cls(renderer=renderer)

    @pytest.mark.asyncio
    async def test_counter_example_renders(
        self, controller: object, renderer: MagicMock
    ) -> None:
        result = await controller.counter_example()
        assert result == "rendered"
        renderer.render_page.assert_called_once()
        args, _ = renderer.render_page.call_args
        assert args[1] == "Counter Component Example"

    @pytest.mark.asyncio
    async def test_wizard_example_renders(
        self, controller: object, renderer: MagicMock
    ) -> None:
        result = await controller.wizard_example()
        assert result == "rendered"
        renderer.render_page.assert_called_once()
        args, _ = renderer.render_page.call_args
        assert args[1] == "Form Wizard Example"

    @pytest.mark.asyncio
    async def test_counter_example_renders(
        self, controller: object, renderer: MagicMock
    ) -> None:
        result = await controller.counter_example()
        assert result == "rendered"
        renderer.render_page.assert_called_once()
        _, kwargs = renderer.render_page.call_args
        assert kwargs["title"] == "Counter Component Example"

    @pytest.mark.asyncio
    async def test_wizard_example_renders(
        self, controller: object, renderer: MagicMock
    ) -> None:
        result = await controller.wizard_example()
        assert result == "rendered"
        renderer.render_page.assert_called_once()
        _, kwargs = renderer.render_page.call_args
        assert kwargs["title"] == "Form Wizard Example"

    @pytest.mark.asyncio
    async def test_index_renders(self, controller: object, renderer: MagicMock) -> None:
        result = await controller.index()
        assert result == "rendered"
        renderer.render_page.assert_called_once()
        _, kwargs = renderer.render_page.call_args
        assert kwargs["title"] == "Component Showcase"

    def test_counter_has_get_decorator(self) -> None:
        Cls = _built["ShowcaseController"]
        cfg = Cls.counter_example._route_config
        assert cfg["method"] == "GET"
        assert cfg["path"] == "/showcase/counter"

    def test_wizard_has_get_decorator(self) -> None:
        Cls = _built["ShowcaseController"]
        cfg = Cls.wizard_example._route_config
        assert cfg["method"] == "GET"
        assert cfg["path"] == "/showcase/wizard"

    def test_index_has_get_decorator(self) -> None:
        Cls = _built["ShowcaseController"]
        cfg = Cls.index._route_config
        assert cfg["method"] == "GET"
        assert cfg["path"] == "/showcase"
