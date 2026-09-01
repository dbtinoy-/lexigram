from __future__ import annotations

import pytest

from lexigram.admin.schema import (
    MarkdownField,
    RichTextField,
    SchemaField,
    TextAreaField,
    TextField,
)
from lexigram.admin.schema import text_area as text_area_module
from lexigram.result import Ok
from lexigram.ui import Element


class TestTextAreaField:
    def test_construct_with_minimum_args(self) -> None:
        field = TextAreaField(name="bio")
        assert field.name == "bio"
        assert isinstance(field, SchemaField)
        assert isinstance(field, TextField)

    def test_construct_with_all_args(self) -> None:
        field = TextAreaField(
            name="bio",
            label="Biography",
            placeholder="Tell us about yourself",
            rows=8,
        )
        assert field.label == "Biography"
        assert field.placeholder == "Tell us about yourself"
        assert field.rows == 8

    def test_render_form_returns_element(self) -> None:
        field = TextAreaField(name="bio")
        element = field.render_form("Hello")
        assert isinstance(element, Element)

    def test_render_form_with_name_and_value(self) -> None:
        field = TextAreaField(name="bio")
        output = str(field.render_form("Hello world"))
        assert 'name="bio"' in output
        assert "Hello world" in output

    def test_render_form_with_rows(self) -> None:
        field = TextAreaField(name="bio", rows=12)
        output = str(field.render_form(None))
        assert 'rows="12"' in output

    def test_render_form_with_placeholder(self) -> None:
        field = TextAreaField(name="bio", placeholder="Type here")
        output = str(field.render_form(None))
        assert 'placeholder="Type here"' in output

    def test_render_form_with_label(self) -> None:
        field = TextAreaField(name="bio", label="Biography")
        output = str(field.render_form(None))
        assert "Biography" in output

    def test_render_form_with_error(self) -> None:
        field = TextAreaField(name="bio", label="Biography")
        output = str(field.render_form(None, errors=["Required"]))
        assert "Required" in output

    def test_render_form_readonly_disables(self) -> None:
        field = TextAreaField(name="bio", readonly=True)
        output = str(field.render_form("locked"))
        assert "disabled" in output

    def test_render_column_with_none(self) -> None:
        field = TextAreaField(name="bio")
        output = str(field.render_column(None, None))
        assert "\u2014" in output

    def test_render_column_truncates_long(self) -> None:
        field = TextAreaField(name="bio")
        value = "x" * 250
        output = str(field.render_column(None, value))
        assert output.startswith("<span")
        assert "..." in output

    def test_render_column_short(self) -> None:
        field = TextAreaField(name="bio")
        output = str(field.render_column(None, "short"))
        assert "short" in output
        assert "..." not in output

    def test_from_form_returns_ok(self) -> None:
        field = TextAreaField(name="bio")
        result = field.from_form("hello")
        assert isinstance(result, Ok)
        assert result.unwrap() == "hello"


class TestMarkdownField:
    def test_construct_with_minimum_args(self) -> None:
        field = MarkdownField(name="body")
        assert field.name == "body"
        assert isinstance(field, TextAreaField)

    def test_construct_with_all_args(self) -> None:
        field = MarkdownField(name="body", preview=False, min_height=500)
        assert field.preview is False
        assert field.min_height == 500

    def test_render_form_returns_element(self) -> None:
        field = MarkdownField(name="body")
        element = field.render_form("# Title")
        assert isinstance(element, Element)

    def test_render_form_with_name_and_value(self) -> None:
        field = MarkdownField(name="body")
        output = str(field.render_form("# Hello"))
        assert 'name="body"' in output
        assert "# Hello" in output

    def test_render_form_preview_toggle_present(self) -> None:
        field = MarkdownField(name="body")
        output = str(field.render_form("text"))
        assert "Preview" in output
        assert "Edit" in output

    def test_render_form_with_preview_disabled(self) -> None:
        field = MarkdownField(name="body", preview=False)
        output = str(field.render_form("text"))
        assert "Preview" not in output

    def test_render_form_with_min_height(self) -> None:
        field = MarkdownField(name="body", min_height=420)
        output = str(field.render_form(None))
        assert "min-height: 420px" in output

    def test_render_form_readonly_disables(self) -> None:
        field = MarkdownField(name="body", readonly=True)
        output = str(field.render_form("text"))
        assert "disabled" in output

    def test_render_column_strips_markdown(self) -> None:
        field = MarkdownField(name="body")
        output = str(field.render_column(None, "**bold** and `code`"))
        assert "bold" in output
        assert "**" not in output

    def test_render_column_with_none(self) -> None:
        field = MarkdownField(name="body")
        output = str(field.render_column(None, None))
        assert "\u2014" in output


class TestRichTextField:
    def test_construct_with_minimum_args(self) -> None:
        field = RichTextField(name="content")
        assert field.name == "content"
        assert isinstance(field, TextAreaField)

    def test_construct_with_all_args(self) -> None:
        field = RichTextField(
            name="content",
            toolbar="bold italic",
            min_height=500,
        )
        assert field.toolbar == "bold italic"
        assert field.min_height == 500

    def test_render_form_returns_element(self) -> None:
        field = RichTextField(name="content")
        element = field.render_form("<p>Hello</p>")
        assert isinstance(element, Element)

    def test_render_form_with_trix_editor(self) -> None:
        field = RichTextField(name="content")
        output = str(field.render_form("<p>Hello</p>"))
        assert "<trix-editor" in output

    def test_render_form_hidden_input_has_initial_value(self) -> None:
        field = RichTextField(name="content")
        output = str(field.render_form("<p>Hello</p>"))
        assert 'name="content"' in output
        assert 'id="content_input"' in output
        assert "&lt;p&gt;Hello&lt;/p&gt;" in output

    def test_render_form_toolbar_passes_through(self) -> None:
        field = RichTextField(name="content", toolbar="bold italic")
        output = str(field.render_form(None))
        assert 'data-toolbar="bold italic"' in output

    def test_render_form_with_min_height(self) -> None:
        field = RichTextField(name="content", min_height=400)
        output = str(field.render_form(None))
        assert "min-height: 400px" in output

    def test_render_form_readonly_disables(self) -> None:
        field = RichTextField(name="content", readonly=True)
        output = str(field.render_form("text"))
        assert "disabled" in output

    def test_render_assets_returns_element(self) -> None:
        asset = RichTextField.render_assets()
        assert isinstance(asset, Element)
        output = str(asset)
        assert 'rel="stylesheet"' in output
        assert "trix.css" in output
        assert "trix" in output
        assert "<script" in output

    def test_render_assets_uses_vendored_static_paths(self) -> None:
        """Trix loads from the admin static mount, never a CDN (doc 03)."""
        output = str(RichTextField.render_assets())
        assert "/admin/static/css/trix.css" in output
        assert "/admin/static/js/trix.umd.min.js" in output
        assert "unpkg.com" not in output
        assert "cdn.jsdelivr.net" not in output

    def test_render_assets_honours_custom_prefix(self) -> None:
        output = str(RichTextField.render_assets(asset_prefix="/panel"))
        assert "/panel/static/css/trix.css" in output
        assert "/panel/static/js/trix.umd.min.js" in output

    def test_vendored_trix_assets_exist(self) -> None:
        """The static files referenced by render_assets are shipped."""
        import lexigram.admin as admin_pkg
        from pathlib import Path

        static = Path(admin_pkg.__file__).parent / "static"
        assert (static / "css" / "trix.css").is_file()
        assert (static / "js" / "trix.umd.min.js").is_file()

    def test_render_column_renders_html(self) -> None:
        pytest.importorskip("nh3", reason="HTML sanitization requires nh3")
        field = RichTextField(name="content")
        output = str(field.render_column(None, "<p>Hello</p>"))
        assert "<p>Hello</p>" in output

    def test_render_column_sanitizes_script_tags(self) -> None:
        pytest.importorskip("nh3", reason="HTML sanitization requires nh3")
        field = RichTextField(name="content")
        output = str(field.render_column(None, "<p>hi</p><script>alert(1)</script>"))
        assert "<p>hi</p>" in output
        assert "<script>" not in output
        assert "alert(1)" not in output

    def test_render_column_strips_event_handler_attributes(self) -> None:
        pytest.importorskip("nh3", reason="HTML sanitization requires nh3")
        field = RichTextField(name="content")
        output = str(field.render_column(None, '<img src=x onerror="alert(1)">'))
        assert "<img" not in output
        assert "onerror" not in output

    def test_render_column_strips_javascript_urls(self) -> None:
        pytest.importorskip("nh3", reason="HTML sanitization requires nh3")
        field = RichTextField(name="content")
        output = str(
            field.render_column(None, '<a href="javascript:alert(1)">click</a>')
        )
        assert "javascript:" not in output
        assert "click" in output

    def test_render_column_fail_closed_when_nh3_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raise_import_error(_value: str) -> str:
            raise ImportError("nh3 not installed")

        monkeypatch.setattr(text_area_module, "sanitize_html", raise_import_error)
        field = RichTextField(name="content")
        output = str(field.render_column(None, "<p>hi</p>"))
        assert "&lt;p&gt;hi&lt;/p&gt;" in output
        assert "<p>hi</p>" not in output

    def test_render_column_with_none(self) -> None:
        field = RichTextField(name="content")
        output = str(field.render_column(None, None))
        assert "\u2014" in output

    def test_from_form_returns_ok(self) -> None:
        field = RichTextField(name="content")
        result = field.from_form("<p>hi</p>")
        assert isinstance(result, Ok)
        assert result.unwrap() == "<p>hi</p>"
