"""Tests for layout mixins: CSSManager, JSManager."""
from __future__ import annotations

from lexigram.ui.layouts.mixins import CSSManager, JSManager


class TestCSSManager:
    def test_init_empty(self) -> None:
        mgr = CSSManager()
        assert mgr.render_css() == ""

    def test_add_css_file(self) -> None:
        mgr = CSSManager()
        mgr.add_css("/styles.css")
        result = mgr.render_css()
        assert 'href="/styles.css"' in result
        assert 'rel="stylesheet"' in result

    def test_add_css_file_with_attrs(self) -> None:
        mgr = CSSManager()
        mgr.add_css("/print.css", media="print")
        result = mgr.render_css()
        assert 'href="/print.css"' in result
        assert 'media="print"' in result

    def test_add_inline_style(self) -> None:
        mgr = CSSManager()
        mgr.add_inline_style("body { color: red; }")
        result = mgr.render_css()
        assert "body { color: red; }" in result
        assert "<style>" in result

    def test_add_multiple_css(self) -> None:
        mgr = CSSManager()
        mgr.add_css("a.css")
        mgr.add_css("b.css")
        result = mgr.render_css()
        assert result.count("href=") == 2

    def test_mixed_css_and_inline(self) -> None:
        mgr = CSSManager()
        mgr.add_css("main.css")
        mgr.add_inline_style("h1 { }")
        result = mgr.render_css()
        assert "main.css" in result
        assert "h1" in result


class TestJSManager:
    def test_init_empty(self) -> None:
        mgr = JSManager()
        assert mgr.render_js_head() == ""
        assert mgr.render_js_body_end() == ""

    def test_add_js_file(self) -> None:
        mgr = JSManager()
        mgr.add_js("/app.js")
        result = mgr.render_js_head()
        assert 'src="/app.js"' in result

    def test_add_js_deferred(self) -> None:
        mgr = JSManager()
        mgr.add_js("/deferred.js", defer=True)
        head = mgr.render_js_head()
        assert 'src="/deferred.js"' in head
        assert "defer" in head

    def test_add_js_async(self) -> None:
        mgr = JSManager()
        mgr.add_js("/async.js", async_=True)
        head = mgr.render_js_head()
        assert "async" in head

    def test_add_js_with_custom_attrs(self) -> None:
        mgr = JSManager()
        mgr.add_js("/module.js", type="module")
        head = mgr.render_js_head()
        assert 'type="module"' in head

    def test_add_inline_script(self) -> None:
        mgr = JSManager()
        mgr.add_inline_script("console.log('hi')")
        head = mgr.render_js_head()
        assert "console.log" in head

    def test_add_inline_script_deferred(self) -> None:
        mgr = JSManager()
        mgr.add_inline_script("console.log('deferred')", defer=True)
        head = mgr.render_js_head()
        assert "console.log" not in head
        body_end = mgr.render_js_body_end()
        assert "console.log" in body_end

    def test_render_js_body_end_empty_when_no_deferred(self) -> None:
        mgr = JSManager()
        mgr.add_inline_script("hello")
        assert mgr.render_js_body_end() == ""

    def test_multiple_js_files(self) -> None:
        mgr = JSManager()
        mgr.add_js("lib.js")
        mgr.add_js("app.js", defer=True)
        result = mgr.render_js_head()
        assert result.count("<script") == 2

    def test_mixed_inline_and_external(self) -> None:
        mgr = JSManager()
        mgr.add_js("external.js")
        mgr.add_inline_script("inline();")
        result = mgr.render_js_head()
        assert "external.js" in result
        assert "inline();" in result
