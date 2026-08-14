"""Tests for LayoutBase."""
from __future__ import annotations

from lexigram.ui.config import BaseLayoutConfig
from lexigram.ui.layouts.base_layout import BaseLayoutContext, LayoutBase


class TestBaseLayoutContext:
    def test_defaults(self) -> None:
        ctx = BaseLayoutContext()
        assert ctx.title == ""
        assert ctx.base_url == "/admin"
        assert ctx.flash_messages == []


class TestLayoutBase:
    def test_init_with_defaults(self) -> None:
        layout = LayoutBase()
        assert layout.theme == "light"
        assert layout.primary_color == "#6b7280"
        assert layout.htmx_enabled is True
        assert layout.htmx_boost is True

    def test_init_with_config(self) -> None:
        config = BaseLayoutConfig(theme="dark", primary_color="#ff0000")
        layout = LayoutBase(config=config)
        assert layout.theme == "dark"
        assert layout.primary_color == "#ff0000"

    def test_render_htmx_head_enabled(self) -> None:
        layout = LayoutBase()
        result = layout.render_htmx_head()
        assert "htmx" in result
        assert "script" in result

    def test_render_htmx_head_disabled(self) -> None:
        config = BaseLayoutConfig(htmx_enabled=False)
        layout = LayoutBase(config=config)
        result = layout.render_htmx_head()
        assert result == ""

    def test_get_htmx_body_attrs_enabled(self) -> None:
        layout = LayoutBase()
        result = layout.get_htmx_body_attrs()
        assert "hx-boost" in result

    def test_get_htmx_body_attrs_disabled(self) -> None:
        config = BaseLayoutConfig(htmx_enabled=False)
        layout = LayoutBase(config=config)
        result = layout.get_htmx_body_attrs()
        assert result == ""

    def test_get_htmx_config(self) -> None:
        layout = LayoutBase()
        config = layout.get_htmx_config()
        assert config["defaultSwapStyle"] == "innerHTML"
        assert config["historyCacheSize"] == 10

    def test_add_css_delegation(self) -> None:
        layout = LayoutBase()
        layout.add_css("/custom.css")
        result = layout.render_css()
        assert "/custom.css" in result

    def test_add_inline_style(self) -> None:
        layout = LayoutBase()
        layout.add_inline_style("body { }")
        result = layout.render_css()
        assert "body { }" in result

    def test_add_js_delegation(self) -> None:
        layout = LayoutBase()
        layout.add_js("/app.js", defer=True)
        result = layout.render_js_head()
        assert "/app.js" in result
        assert "defer" in result

    def test_add_inline_script(self) -> None:
        layout = LayoutBase()
        layout.add_inline_script("init()", defer=False)
        result = layout.render_js_head()
        assert "init()" in result

    def test_get_theme_html_attrs(self) -> None:
        layout = LayoutBase()
        result = layout.get_theme_html_attrs()
        assert 'data-theme="light"' in result

    def test_render_default_content(self) -> None:
        layout = LayoutBase()
        result = layout.render(content="Hello", title="Test Page")
        assert "<!DOCTYPE html>" in result
        assert "Hello" in result
        assert "Test Page" in result

    def test_render_body_content_default(self) -> None:
        layout = LayoutBase()
        result = layout.render_body_content(content="Body")
        assert result == "Body"

    def test_get_body_attributes(self) -> None:
        layout = LayoutBase()
        result = layout.get_body_attributes()
        assert "data-theme" in result
        assert "hx-boost" in result

    def test_render_body_end_no_flash(self) -> None:
        layout = LayoutBase()
        result = layout.render_body_end()
        assert "alpine:init" in result
        assert "themeToggle" in result

    def test_render_head_content(self) -> None:
        layout = LayoutBase()
        result = layout.render_head_content()
        assert "htmx" in result or "style" in result or "link" in result

    def test_render_with_context_title(self) -> None:
        ctx = BaseLayoutContext(title="Context Title")
        layout = LayoutBase(context=ctx)
        result = layout.render(content="Hi")
        assert "Context Title" in result

    def test_render_with_css_js_config(self) -> None:
        config = BaseLayoutConfig(
            css_files=["/extra.css"],
            js_files=["/extra.js"],
        )
        layout = LayoutBase(config=config)
        result = layout.render_css()
        assert "/extra.css" in result
        js = layout.render_js_head()
        assert "/extra.js" in js

    def test_render_alpine_enabled(self) -> None:
        config = BaseLayoutConfig(include_alpine=True)
        layout = LayoutBase(config=config)
        head = layout.render_head_content()
        assert "alpinejs" in head

    def test_render_flash_script(self) -> None:
        ctx = BaseLayoutContext(
            flash_messages=[("success", "Saved!"), ("error", "Failed!")]
        )
        layout = LayoutBase(context=ctx)
        body_end = layout.render_body_end()
        assert "showToast" in body_end
        assert "Saved!" in body_end
        assert "Failed!" in body_end
