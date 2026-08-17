"""Escape-by-default tests for the ``el()`` render primitive.

Verifies D1 of the XSS/output-rendering remediation: plain ``str`` children
of ``el()``/``Element`` are escaped in text context, while the explicit
opt-outs (``raw()``/``RawHTML``, ``markupsafe.Markup``) and the top-level
``render_to_string(str)`` fragment contract pass through verbatim.
"""

from __future__ import annotations

from markupsafe import Markup

from lexigram.ui.core.base import el, raw, render_to_string


class TestStringChildrenEscaped:
    """Plain ``str`` children are escaped in text context (audit PoC)."""

    def test_audit_poc_script_escaped(self) -> None:
        output = render_to_string(el("div", "<script>alert(1)</script>"))
        assert "<script>alert(1)</script>" not in output
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in output

    def test_quotes_not_escaped_in_text_context(self) -> None:
        output = render_to_string(el("div", "He said \"hi\" and 'bye'"))
        assert "He said \"hi\" and 'bye'" in output

    def test_ampersand_escaped(self) -> None:
        output = render_to_string(el("div", "Tom & Jerry < 3"))
        assert "Tom &amp; Jerry &lt; 3" in output

    def test_nested_elements_still_render(self) -> None:
        output = render_to_string(el("div", el("span", "<b>"), "</div>"))
        assert "<span>&lt;b&gt;</span>" in output


class TestOptOutsPassThrough:
    """``raw()``/``RawHTML`` and ``Markup`` children are inserted verbatim."""

    def test_raw_passthrough(self) -> None:
        output = render_to_string(el("div", raw("<b>ok</b>")))
        assert "<b>ok</b>" in output
        assert "&lt;b&gt;" not in output

    def test_markup_passthrough(self) -> None:
        output = render_to_string(el("div", Markup("<b>ok</b>")))
        assert "<b>ok</b>" in output
        assert "&lt;b&gt;" not in output

    def test_markup_child_not_double_escaped(self) -> None:
        output = render_to_string(el("div", Markup("&amp;")))
        assert "&amp;" in output
        assert "&amp;amp;" not in output

    def test_mixed_children_escape_only_plain_strings(self) -> None:
        output = render_to_string(
            el("div", "<script>", raw("<b>ok</b>"), Markup("<i>em</i>"))
        )
        assert "&lt;script&gt;" in output
        assert "<b>ok</b>" in output
        assert "<i>em</i>" in output


class TestAttributeEscapingUnchanged:
    """Attribute values keep their quote=True escaping (D1 leaves them alone)."""

    def test_attribute_value_escaped(self) -> None:
        output = render_to_string(el("div", {"data-x": '<script>alert(1)</script>"'}))
        assert 'data-x="&lt;script&gt;alert(1)&lt;/script&gt;&quot;"' in output

    def test_attribute_value_ampersand_escaped(self) -> None:
        output = render_to_string(el("div", {"data-x": "a&b"}))
        assert 'data-x="a&amp;b"' in output


class TestRenderToStringContract:
    """Top-level ``render_to_string(str)`` stays verbatim (fragment injection)."""

    def test_top_level_string_verbatim(self) -> None:
        assert render_to_string("<b>ok</b>") == "<b>ok</b>"

    def test_element_string_repr_escapes(self) -> None:
        assert str(el("div", "<b>")) == "<div>&lt;b&gt;</div>"
