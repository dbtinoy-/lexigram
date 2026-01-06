"""Tests for the new rich field types and language switcher."""

from __future__ import annotations

import pytest

from lexigram.admin.forms.fields import (
    ColorField,
    FieldRegistry,
    FieldType,
    KeyValueField,
    MarkdownField,
    RichTextField,
    TagsField,
)
from lexigram.admin.ui.organisms.topbar import LanguageSwitcher


# ---------------------------------------------------------------------------
# FieldType enum
# ---------------------------------------------------------------------------


class TestFieldTypeEnum:
    def test_rich_text_value(self) -> None:
        assert FieldType.RICH_TEXT == "rich_text"

    def test_markdown_value(self) -> None:
        assert FieldType.MARKDOWN == "markdown"

    def test_color_value(self) -> None:
        assert FieldType.COLOR == "color"

    def test_tags_value(self) -> None:
        assert FieldType.TAGS == "tags"

    def test_key_value_value(self) -> None:
        assert FieldType.KEY_VALUE == "key_value"


# ---------------------------------------------------------------------------
# FieldRegistry — new types are registered
# ---------------------------------------------------------------------------


class TestFieldRegistryNewTypes:
    def test_rich_text_registered(self) -> None:
        assert FieldRegistry.has_type(FieldType.RICH_TEXT)

    def test_markdown_registered(self) -> None:
        assert FieldRegistry.has_type(FieldType.MARKDOWN)

    def test_color_registered(self) -> None:
        assert FieldRegistry.has_type(FieldType.COLOR)

    def test_tags_registered(self) -> None:
        assert FieldRegistry.has_type(FieldType.TAGS)

    def test_key_value_registered(self) -> None:
        assert FieldRegistry.has_type(FieldType.KEY_VALUE)

    def test_rich_text_widget_class(self) -> None:
        widget = FieldRegistry.get_widget(FieldType.RICH_TEXT)
        assert widget is RichTextField

    def test_markdown_widget_class(self) -> None:
        widget = FieldRegistry.get_widget(FieldType.MARKDOWN)
        assert widget is MarkdownField

    def test_color_widget_class(self) -> None:
        widget = FieldRegistry.get_widget(FieldType.COLOR)
        assert widget is ColorField

    def test_tags_widget_class(self) -> None:
        widget = FieldRegistry.get_widget(FieldType.TAGS)
        assert widget is TagsField


# ---------------------------------------------------------------------------
# RichTextField
# ---------------------------------------------------------------------------


class TestRichTextField:
    def test_render_produces_component(self) -> None:
        field = RichTextField(name="body", label="Body")
        field.bind("<p>Hello</p>")
        result = field.render()
        assert result is not None

    def test_name_propagated(self) -> None:
        field = RichTextField(name="content")
        result = field.render()
        html = str(result)
        assert "content" in html

    def test_value_propagated(self) -> None:
        field = RichTextField(name="desc")
        field.bind("<b>Bold</b>")
        result = field.render()
        html = str(result)
        assert "Bold" in html or "desc" in html


# ---------------------------------------------------------------------------
# MarkdownField
# ---------------------------------------------------------------------------


class TestMarkdownField:
    def test_render_produces_component(self) -> None:
        field = MarkdownField(name="notes", label="Notes")
        field.bind("# Title")
        result = field.render()
        assert result is not None

    def test_name_in_html(self) -> None:
        field = MarkdownField(name="readme")
        result = field.render()
        assert "readme" in str(result)


# ---------------------------------------------------------------------------
# ColorField
# ---------------------------------------------------------------------------


class TestColorField:
    def test_render_produces_component(self) -> None:
        field = ColorField(name="brand_color")
        field.bind("#ff0000")
        result = field.render()
        assert result is not None

    def test_color_type_in_html(self) -> None:
        field = ColorField(name="color")
        html = str(field.render())
        assert "color" in html.lower()


# ---------------------------------------------------------------------------
# TagsField
# ---------------------------------------------------------------------------


class TestTagsField:
    def test_render_produces_component(self) -> None:
        field = TagsField(name="tags")
        field.bind(["python", "admin"])
        result = field.render()
        assert result is not None

    def test_name_in_output(self) -> None:
        field = TagsField(name="my_tags")
        html = str(field.render())
        assert "my_tags" in html


# ---------------------------------------------------------------------------
# KeyValueField
# ---------------------------------------------------------------------------


class TestKeyValueField:
    def test_render_produces_component(self) -> None:
        field = KeyValueField(name="meta")
        field.bind({"env": "prod"})
        result = field.render()
        assert result is not None

    def test_name_in_output(self) -> None:
        field = KeyValueField(name="attrs")
        html = str(field.render())
        assert "attrs" in html


# ---------------------------------------------------------------------------
# LanguageSwitcher
# ---------------------------------------------------------------------------


class TestLanguageSwitcher:
    def test_render_returns_component(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("fr", "Français")],
            current_locale="en",
        )
        html = str(sw.render())
        assert html is not None

    def test_contains_locale_options(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("de", "Deutsch")],
            current_locale="de",
        )
        html = str(sw.render())
        assert "en" in html
        assert "de" in html

    def test_action_url_in_form(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English")],
            action_url="/set-lang",
        )
        html = str(sw.render())
        assert "/set-lang" in html

    def test_default_action_url(self) -> None:
        sw = LanguageSwitcher()
        html = str(sw.render())
        assert "/admin/set-locale" in html

    def test_current_locale_selected(self) -> None:
        sw = LanguageSwitcher(
            locales=[("en", "English"), ("fr", "Français")],
            current_locale="fr",
        )
        html = str(sw.render())
        assert "fr" in html

    def test_contains_form_element(self) -> None:
        sw = LanguageSwitcher()
        html = str(sw.render())
        assert "form" in html.lower()

    def test_contains_select_element(self) -> None:
        sw = LanguageSwitcher(locales=[("en", "English")])
        html = str(sw.render())
        assert "select" in html.lower()

    def test_multiple_locales(self) -> None:
        locales = [("en", "English"), ("fr", "Français"), ("es", "Español"), ("de", "Deutsch")]
        sw = LanguageSwitcher(locales=locales, current_locale="es")
        html = str(sw.render())
        for code, _ in locales:
            assert code in html

    def test_default_locales(self) -> None:
        sw = LanguageSwitcher()
        assert len(sw.locales) >= 1
