from __future__ import annotations

import pytest

from lexigram.admin.schema import SchemaField
from lexigram.admin.schema.text import (
    EmailField,
    PasswordField,
    TextField,
    URLField,
)
from lexigram.admin.schema.text_area import MarkdownField, RichTextField, TextAreaField
from lexigram.result import Ok
from lexigram.ui import Element, InfolistEntryType


class TestTextField:
    def test_construct_with_minimum_args(self) -> None:
        field = TextField(name="username")
        assert field.name == "username"

    def test_construct_with_all_args(self) -> None:
        field = TextField(
            name="username",
            label="Username",
            help_text="Enter your username",
            placeholder="user123",
            required=True,
        )
        assert field.name == "username"
        assert field.label == "Username"
        assert field.help_text == "Enter your username"
        assert field.placeholder == "user123"
        assert field.required is True

    def test_render_form_returns_element(self) -> None:
        field = TextField(name="username")
        element = field.render_form("hello")
        assert isinstance(element, Element)

    def test_render_form_with_value(self) -> None:
        field = TextField(name="username")
        element = field.render_form("hello")
        output = str(element)
        assert "hello" in output

    def test_render_form_with_none(self) -> None:
        field = TextField(name="username")
        element = field.render_form(None)
        output = str(element)
        assert 'value=""' in output

    def test_render_form_with_errors(self) -> None:
        field = TextField(name="username", label="Username")
        element = field.render_form("hello", errors=["Required"])
        output = str(element)
        assert "Required" in output

    def test_render_column_with_value(self) -> None:
        field = TextField(name="username")
        element = field.render_column(None, "hello")
        output = str(element)
        assert "hello" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = TextField(name="username")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = TextField(name="username")
        assert field.render_filter() is None

    def test_from_form_strips_whitespace(self) -> None:
        field = TextField(name="username")
        result = field.from_form("  hello  ")
        assert isinstance(result, Ok)
        assert result.unwrap() == "hello"

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = TextField(name="username", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = TextField(name="username")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_value(self) -> None:
        field = TextField(name="username")
        assert field.to_form("hello") == "hello"

    def test_to_form_with_none(self) -> None:
        field = TextField(name="username")
        assert field.to_form(None) == ""

    def test_label_defaults_to_none(self) -> None:
        field = TextField(name="username")
        assert field.label is None

    def test_is_schema_field(self) -> None:
        field = TextField(name="username")
        assert isinstance(field, SchemaField)


class TestEmailField:
    def test_construct(self) -> None:
        field = EmailField(name="email")
        assert field.name == "email"

    def test_render_infolist_entry_email_type(self) -> None:
        field = EmailField(name="email")
        entry = field.render_infolist_entry("user@example.com")
        assert entry.type == InfolistEntryType.EMAIL
        assert entry.value == "user@example.com"

    def test_render_form_type_email(self) -> None:
        field = EmailField(name="email")
        element = field.render_form("user@example.com")
        output = str(element)
        assert 'type="email"' in output
        assert "user@example.com" in output

    def test_render_column_mailto(self) -> None:
        field = EmailField(name="email")
        element = field.render_column(None, "user@example.com")
        output = str(element)
        assert 'href="mailto:user@example.com"' in output
        assert "user@example.com" in output

    def test_render_column_none(self) -> None:
        field = EmailField(name="email")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_filter_returns_none(self) -> None:
        field = EmailField(name="email")
        assert field.render_filter() is None

    def test_inherits_from_form(self) -> None:
        field = EmailField(name="email")
        result = field.from_form("  user@example.com  ")
        assert isinstance(result, Ok)
        assert result.unwrap() == "user@example.com"


class TestPasswordField:
    def test_construct(self) -> None:
        field = PasswordField(name="password")
        assert field.name == "password"

    def test_render_form_type_password(self) -> None:
        field = PasswordField(name="password")
        element = field.render_form("secret123")
        output = str(element)
        assert 'type="password"' in output

    def test_render_column_masked(self) -> None:
        field = PasswordField(name="password")
        element = field.render_column(None, "secret123")
        output = str(element)
        assert "secret123" not in output
        assert "••••••" in output

    def test_render_infolist_entry_masked(self) -> None:
        field = PasswordField(name="password")
        entry = field.render_infolist_entry("secret123")
        assert entry.type == InfolistEntryType.TEXT
        assert entry.value == "••••••"

    def test_render_infolist_entry_none_value(self) -> None:
        field = PasswordField(name="password")
        entry = field.render_infolist_entry(None)
        assert entry.type == InfolistEntryType.TEXT
        assert entry.value is None

    def test_render_column_none(self) -> None:
        field = PasswordField(name="password")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_filter_returns_none(self) -> None:
        field = PasswordField(name="password")
        assert field.render_filter() is None


class TestURLField:
    def test_construct(self) -> None:
        field = URLField(name="url")
        assert field.name == "url"

    def test_render_form_type_url(self) -> None:
        field = URLField(name="url")
        element = field.render_form("https://example.com")
        output = str(element)
        assert 'type="url"' in output
        assert "https://example.com" in output

    def test_render_column_link(self) -> None:
        field = URLField(name="url")
        element = field.render_column(None, "https://example.com")
        output = str(element)
        assert 'href="https://example.com"' in output
        assert "https://example.com" in output

    def test_render_column_rejects_unsafe_scheme(self) -> None:
        field = URLField(name="url")
        output = str(field.render_column(None, "javascript:alert(1)"))

        assert "<a" not in output
        assert "javascript:alert(1)" in output

    def test_render_filter_returns_none(self) -> None:
        field = URLField(name="url")
        assert field.render_filter() is None

    def test_render_infolist_entry_url_type(self) -> None:
        field = URLField(name="url")
        entry = field.render_infolist_entry("https://example.com")
        assert entry.type == InfolistEntryType.URL
        assert entry.value == "https://example.com"


class TestTextAreaField:
    def test_construct_default_rows(self) -> None:
        field = TextAreaField(name="bio")
        assert field.name == "bio"
        assert field.rows == 5

    def test_construct_custom_rows(self) -> None:
        field = TextAreaField(name="bio", rows=10)
        assert field.rows == 10

    def test_render_form(self) -> None:
        field = TextAreaField(name="bio")
        element = field.render_form("Hello")
        output = str(element)
        assert "Hello" in output
        assert "textarea" in output.lower()

    def test_render_column_truncates_long_text(self) -> None:
        field = TextAreaField(name="bio")
        long_text = "a" * 300
        element = field.render_column(None, long_text)
        output = str(element)
        assert len(output) < 250
        assert "..." in output

    def test_render_column_short_text(self) -> None:
        field = TextAreaField(name="bio")
        element = field.render_column(None, "Hello")
        output = str(element)
        assert "Hello" in output
        assert "..." not in output

    def test_render_column_none(self) -> None:
        field = TextAreaField(name="bio")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_filter_returns_none(self) -> None:
        field = TextAreaField(name="bio")
        assert field.render_filter() is None


class TestMarkdownField:
    def test_render_form(self) -> None:
        field = MarkdownField(name="content")
        element = field.render_form("# Hello")
        output = str(element)
        assert "# Hello" in output
        assert "textarea" in output.lower()

    def test_render_column_plain_text(self) -> None:
        field = MarkdownField(name="content")
        element = field.render_column(None, "# Hello **world**")
        output = str(element)
        assert "Hello" in output
        assert "<h1>" not in output
        assert "<strong>" not in output

    def test_render_column_none(self) -> None:
        field = MarkdownField(name="content")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output


class TestRichTextField:
    pytest.importorskip("nh3", reason="HTML sanitization requires nh3")

    def test_render_form(self) -> None:
        field = RichTextField(name="content")
        element = field.render_form("<p>Hello</p>")
        output = str(element)
        assert "<p>Hello</p>" in output or "Hello" in output

    def test_render_column_html(self) -> None:
        field = RichTextField(name="content")
        element = field.render_column(None, "<p>Hello <strong>World</strong></p>")
        output = str(element)
        assert "<p>" in output
        assert "<strong" in output

    def test_render_column_none(self) -> None:
        field = RichTextField(name="content")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
