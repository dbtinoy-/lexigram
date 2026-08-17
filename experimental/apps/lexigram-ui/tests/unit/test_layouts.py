"""Tests for layout components — HTMLDocument, LayoutBase, Stack."""

from __future__ import annotations

from typing import Any

from lexigram.ui.config import HTMLDocumentConfig
from lexigram.ui.layouts.html_document import HTMLDocument
from lexigram.ui.molecules.stack import Stack


class TestHTMLDocument:
    """Tests for the base HTML document generator."""

    def test_renders_doctype(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert html.startswith("<!DOCTYPE html>")

    def test_renders_html_tag_with_lang(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert '<html lang="en">' in html

    def test_renders_head_and_body(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert "<head>" in html
        assert "<body>" in html

    def test_title_in_head(self) -> None:
        doc = _make_doc()
        html = str(doc.render("My Page"))
        assert "<title>My Page</title>" in html

    def test_charset_meta(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert 'charset="UTF-8"' in html

    def test_viewport_meta(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert 'name="viewport"' in html

    def test_custom_config(self) -> None:
        config = HTMLDocumentConfig(
            lang="fr",
            description="French page",
            keywords=["french", "test"],
            author="Test Author",
            robots="noindex",
        )
        doc = _make_doc(config=config)
        html = str(doc.render("Bonjour"))
        assert '<html lang="fr">' in html
        assert 'content="French page"' in html
        assert 'content="french, test"' in html
        assert 'content="noindex"' in html

    def test_favicon(self) -> None:
        config = HTMLDocumentConfig(favicon="/favicon.ico")
        doc = _make_doc(config=config)
        html = str(doc.render("Test"))
        assert 'href="/favicon.ico"' in html

    def test_open_graph(self) -> None:
        config = HTMLDocumentConfig(
            og_title="OG Title",
            og_description="OG Desc",
            og_image="/image.png",
            og_url="https://example.com",
        )
        doc = _make_doc(config=config)
        html = str(doc.render("Test"))
        assert 'property="og:title"' in html
        assert 'content="OG Title"' in html
        assert 'content="OG Desc"' in html
        assert 'content="/image.png"' in html

    def test_theme_color_meta(self) -> None:
        config = HTMLDocumentConfig(theme_color="#663399")
        doc = _make_doc(config=config)
        html = str(doc.render("Test"))
        assert 'content="#663399"' in html

    def test_extra_head(self) -> None:
        config = HTMLDocumentConfig(extra_head="<link rel='preload' href='/font.woff2'>")
        doc = _make_doc(config=config)
        html = str(doc.render("Test"))
        assert "preload" in html

    def test_render_body_content_is_abstract(self) -> None:
        doc = _make_doc()
        html = str(doc.render("Test"))
        assert "BODY_CONTENT" in html

    def test_empty_title_omits_title_tag(self) -> None:
        doc = _make_doc()
        html = str(doc.render(""))
        assert "<title>" not in html

    def test_custom_config_empty_keywords_no_tag(self) -> None:
        config = HTMLDocumentConfig(keywords=[])
        doc = _make_doc(config=config)
        html = str(doc.render("Test"))
        assert 'name="keywords"' not in html


class TestStack:
    """Tests for the Stack layout component."""

    def test_renders_flex_container(self) -> None:
        stack = Stack()
        html = str(stack)
        assert "flex flex-col" in html

    def test_gap_class(self) -> None:
        stack = Stack(gap=6)
        html = str(stack)
        assert "gap-6" in html

    def test_default_gap_is_4(self) -> None:
        stack = Stack()
        html = str(stack)
        assert "gap-4" in html

    def test_custom_class(self) -> None:
        stack = Stack(class_="my-stack extra")
        html = str(stack)
        assert "my-stack" in html
        assert "extra" in html

    def test_renders_children(self) -> None:
        from lexigram.ui.core.base import el

        stack = Stack(children=[el("div", "child1"), el("span", "child2")])
        html = str(stack)
        assert "child1" in html
        assert "child2" in html

    def test_empty_children(self) -> None:
        stack = Stack()
        html = str(stack)
        assert "<div" in html

    def test_implements_html_method(self) -> None:
        from lexigram.ui.core.base import el

        children = [el("p", "item")]
        stack = Stack(children=children)
        result = stack.__html__()
        assert "item" in result
        assert "flex flex-col" in result

    def test_default_class_empty(self) -> None:
        stack = Stack()
        html = str(stack)
        assert "flex flex-col gap-4" in html


class TestLayoutBase:
    """Tests for the LayoutBase class (extends HTMLDocument)."""

    def test_inherits_from_html_document(self) -> None:
        from lexigram.ui.layouts.base_layout import LayoutBase

        assert issubclass(LayoutBase, HTMLDocument)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TestDoc(HTMLDocument):
    """Concrete HTMLDocument subclass for testing."""

    def render_head_content(self, **context: Any) -> str:  # type: ignore[no-untyped-def]
        return ""

    def render_body_content(self, **context: Any) -> str:  # type: ignore[no-untyped-def]
        return "BODY_CONTENT"

    def render_body_end(self, **context: Any) -> str:  # type: ignore[no-untyped-def]
        return ""


def _make_doc(config: HTMLDocumentConfig | None = None) -> _TestDoc:
    return _TestDoc(config=config)
