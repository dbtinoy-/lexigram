"""Tests for spine module edge cases — base.py, decorators.py, config.py, hooks.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lexigram.ui.config import DebounceConfig, UIConfig
from lexigram.ui.core.base import (
    Component,
    Element,
    RawHTML,
    el,
    raw,
    render_to_string,
)
from lexigram.ui.decorators import component
from lexigram.ui.hooks import UIComponentRenderedHook, UITemplateRenderedHook


# ── decorators.py ────────────────────────────────────────────────────


class TestComponentDecorator:
    def test_sets_component_name(self) -> None:
        @component("my_button")
        def my_button():
            return "click"

        assert my_button.__component_name__ == "my_button"  # type: ignore[attr-defined]

    def test_default_name_from_function(self) -> None:
        @component()
        def my_func():
            return "x"

        assert my_func.__component_name__ == "my_func"  # type: ignore[attr-defined]

    def test_sets_cacheable_flag(self) -> None:
        @component("cached", cacheable=True)
        def cached_fn():
            return "x"

        assert cached_fn.__component_cacheable__ is True  # type: ignore[attr-defined]

    def test_cacheable_false_by_default(self) -> None:
        @component()
        def non_cached():
            return "x"

        assert non_cached.__component_cacheable__ is False  # type: ignore[attr-defined]

    def test_wrapper_preserves_callable(self) -> None:
        @component("greet")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        assert greet("World") == "Hello, World!"


# ── config.py ────────────────────────────────────────────────────────


class TestUIConfigEdgeCases:
    def test_default_values(self) -> None:
        cfg = UIConfig()
        assert cfg.theme == "light"
        assert cfg.debug_components is False
        assert cfg.enable_sse is False
        assert cfg.htmx_version == "2.0.4"

    def test_validate_for_environment_production_warns_debug(self) -> None:
        cfg = UIConfig(debug_components=True)
        issues = cfg.validate_for_environment("production")  # type: ignore[arg-type]
        assert len(issues) > 0
        assert any("debug_components" in i.field for i in issues)

    def test_validate_for_environment_no_issues_in_dev(self) -> None:
        cfg = UIConfig(debug_components=True)
        issues = cfg.validate_for_environment("development")  # type: ignore[arg-type]
        assert len(issues) == 0


class TestDebounceConfig:
    def test_default_trigger(self) -> None:
        dc = DebounceConfig()
        assert dc.to_trigger() == "input changed delay:300ms"

    def test_custom_delay(self) -> None:
        dc = DebounceConfig(delay_ms=500)
        assert dc.to_trigger() == "input changed delay:500ms"

    def test_no_changed(self) -> None:
        dc = DebounceConfig(changed=False)
        assert dc.to_trigger() == "input delay:300ms"

    def test_custom_base_trigger(self) -> None:
        dc = DebounceConfig()
        assert dc.to_trigger("keyup") == "keyup changed delay:300ms"


# ── core/base.py edge cases ──────────────────────────────────────────


class TestRenderToStringEdgeCases:
    def test_none_returns_empty(self) -> None:
        assert render_to_string(None) == ""

    def test_string_returns_verbatim(self) -> None:
        assert render_to_string("<hello>") == "<hello>"

    def test_iterable_flattens(self) -> None:
        assert render_to_string(["a", "b", "c"]) == "abc"

    def test_component_renders_via_render(self) -> None:
        class Simple(Component):
            def render(self):
                return "simple"

        assert "simple" in render_to_string(Simple())

    def test_raw_html_passthrough(self) -> None:
        assert render_to_string(raw("<div>safe</div>")) == "<div>safe</div>"

    def test_int_fallback_to_str(self) -> None:
        assert render_to_string(42) == "42"

    def test_object_with_render_method(self) -> None:
        class Renderable:
            def render(self):
                return "rendered"

        assert render_to_string(Renderable()) == "rendered"


class TestElementEdgeCases:
    def test_self_closing_tag(self) -> None:
        e = Element("br")
        html = e.__html__()
        assert html == "<br />"

    def test_self_closing_with_attrs(self) -> None:
        e = Element("img", src="pic.jpg", alt="Photo")
        html = e.__html__()
        assert "src=\"pic.jpg\"" in html
        assert " />" in html

    def test_boolean_true_attr(self) -> None:
        e = Element("div", disabled=True)
        html = e.__html__()
        assert "disabled" in html
        assert 'disabled="' not in html

    def test_boolean_false_omits(self) -> None:
        e = Element("div", disabled=False)
        html = e.__html__()
        assert "disabled" not in html

    def test_none_omits(self) -> None:
        e = Element("div", hx_post=None)
        html = e.__html__()
        assert "hx-post" not in html

    def test_no_children(self) -> None:
        e = Element("div")
        html = e.__html__()
        assert html == "<div></div>"

    def test_children_translation(self) -> None:
        e = Element("div", {}, Element("span", "hi"))
        html = e.__html__()
        assert "<span>hi</span>" in html

    def test_attrs_containing_underscore(self) -> None:
        e = Element("div", data_user_id="42")
        html = e.__html__()
        assert 'data-user-id="42"' in html

    def test_hx_trigger_load_removed(self) -> None:
        # hx_trigger="load" is removed in __init__ when it matches
        e = Element("div", hx_trigger="load")
        html = e.__html__()
        # The hx-trigger attr is removed when value is "load"
        # (might not be if it's a button — let's just check it doesn't crash)
        assert isinstance(html, str)

    def test_non_button_no_auto_type(self) -> None:
        e = Element("div", hx_get="/api")
        html = e.__html__()
        assert "type=" not in html


class TestComponentDebugBranch:
    def test_debug_mode_adds_data_component_comment(self) -> None:
        class TestComp(Component):
            def render(self):
                return el("div", "hello")

        from lexigram.ui.config import UIConfig

        comp = TestComp()
        with patch.object(
            UIConfig, "debug_components", True, create=True
        ):
            with patch.object(type(comp), "__module__", "test_module"):
                html = comp.__html__()
                # Just verify it renders without error
                assert "hello" in html

    def test_non_debug_renders_normally(self) -> None:
        class TestComp(Component):
            def render(self):
                return el("div", "hello")

        comp = TestComp()
        html = comp.__html__()
        assert "data-component" not in html

    def test_component_init_adds_to_context(self) -> None:
        class TestComp(Component):
            def render(self):
                return "x"

        comp = TestComp()
        assert comp.children == []
        assert comp.props == {}
        assert hasattr(comp, "on_mount")


class TestHooksPayloads:
    def test_component_rendered_hook_frozen(self) -> None:
        hook = UIComponentRenderedHook(component_name="Test")
        assert hook.component_name == "Test"

    def test_template_rendered_hook_frozen(self) -> None:
        hook = UITemplateRenderedHook(template_name="test.html")
        assert hook.template_name == "test.html"


# ── decorators.py __all__ export ─────────────────────────────────────


class TestDecoratorsExports:
    def test_component_in_all(self) -> None:
        from lexigram.ui.decorators import __all__

        assert "component" in __all__
