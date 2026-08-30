"""Escaping-policy tests for the element/component rendering layer.

Policy: *strings are data, elements are structure.*

- Plain strings (including plain-string results of ``Component.render()``)
  are escaped when inserted as Element children.
- ``Markup``, ``raw()`` and any ``__html__``-bearing object pass through
  verbatim — explicit opt-outs for pre-rendered HTML.
"""

from __future__ import annotations

from markupsafe import Markup

from lexigram.ui.core.base import (
    Component,
    el,
    looks_like_html,
    raw,
    render_to_string,
    warn_html_string_render,
)

class _FakeWarningLogger:
    """Stand-in for the structlog logger: read-only proxy otherwise."""

    def __init__(self) -> None:
        self.calls: list = []

    def warning(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class _UserInput(Component):
    """Component that returns a plain string built from record data."""

    def __init__(self, data: str) -> None:
        super().__init__()
        self.data = data

    def render(self):
        return "<b>" + self.data + "</b>"


class _ElementComp(Component):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.data = data

    def render(self):
        return el("b", self.data)


class _RawComp(Component):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.data = data

    def render(self):
        return raw(f"<b>{self.data}</b>")


class _ListComp(Component):
    def __init__(self, items: list[str]) -> None:
        super().__init__()
        self.items = items

    def render(self):
        return [f"<i>{item}</i>" for item in self.items]


class _Outer(Component):
    def render(self):
        return el("div", _UserInput("nested"))


class TestStringChildrenAreData:
    def test_plain_string_escaped(self) -> None:
        assert render_to_string(el("td", "<b>x</b>")) == "<td>&lt;b&gt;x&lt;/b&gt;</td>"

    def test_plain_text_passes_through(self) -> None:
        assert render_to_string(el("td", "hello & goodbye")) == (
            "<td>hello &amp; goodbye</td>"
        )

    def test_none_child_renders_empty(self) -> None:
        assert render_to_string(el("div", None)) == "<div></div>"


class TestExplicitHtmlOptOuts:
    def test_raw_passthrough(self) -> None:
        assert render_to_string(el("td", raw("<b>x</b>"))) == "<td><b>x</b></td>"

    def test_markup_passthrough(self) -> None:
        assert render_to_string(el("td", Markup("<b>x</b>"))) == "<td><b>x</b></td>"

    def test_element_child_keeps_structure(self) -> None:
        assert render_to_string(el("div", el("span", "hi"))) == (
            "<div><span>hi</span></div>"
        )


class TestComponentChildrenNoBypass:
    """Regression: a Component child whose render() returns a plain string
    used to bypass escaping entirely (XSS)."""

    def test_plain_string_component_output_is_escaped(self) -> None:
        out = render_to_string(el("td", _UserInput("<script>alert(1)</script>")))
        assert "<script>" not in out
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
        # The component's own tags are data too, so they are escaped
        assert "<b>" not in out

    def test_element_component_output_not_double_escaped(self) -> None:
        out = render_to_string(el("td", _ElementComp("<script>x</script>")))
        assert out == "<td><b>&lt;script&gt;x&lt;/script&gt;</b></td>"

    def test_raw_component_output_verbatim(self) -> None:
        out = render_to_string(el("td", _RawComp("ok")))
        assert out == "<td><b>ok</b></td>"

    def test_list_of_strings_escaped(self) -> None:
        out = render_to_string(el("div", _ListComp(["a", "b"])))
        assert "<i>" not in out
        assert "&lt;i&gt;a&lt;/i&gt;" in out
        assert "&lt;i&gt;b&lt;/i&gt;" in out

    def test_nested_components(self) -> None:
        out = render_to_string(el("section", _Outer()))
        assert "&lt;b&gt;nested&lt;/b&gt;" in out


class TestTopLevelRenderVerbatim:
    def test_top_level_string_verbatim(self) -> None:
        # render_to_string is the final-output path: escaping happens at the
        # Element boundary, so top-level strings pass through unchanged.
        assert render_to_string("raw <b>string</b>") == "raw <b>string</b>"


class TestLooksLikeHtml:
    def test_detects_tags(self) -> None:
        assert looks_like_html("<span class='x'>y</span>")
        assert looks_like_html("text <b>bold</b>")
        assert looks_like_html("</div>")

    def test_ignores_plain_text(self) -> None:
        assert not looks_like_html("plain text < 5 and > 2")
        assert not looks_like_html("")
        assert not looks_like_html(None)
        assert not looks_like_html(42)


class TestWarnHtmlStringRender:
    def test_warns_once_per_origin_snippet(self, monkeypatch) -> None:
        from lexigram.ui.core import base as ui_base

        fake = _FakeWarningLogger()
        monkeypatch.setattr(ui_base, "logger", fake)
        warn_html_string_render("column 'x'", "<span>a</span>")
        warn_html_string_render("column 'x'", "<span>a</span>")
        assert len(fake.calls) == 1
        assert "renderer_returned_html_string" in fake.calls[0][0][0]

    def test_no_warning_for_plain_text(self, monkeypatch) -> None:
        from lexigram.ui.core import base as ui_base

        fake = _FakeWarningLogger()
        monkeypatch.setattr(ui_base, "logger", fake)
        warn_html_string_render("column 'x'", "just text")
        assert fake.calls == []
