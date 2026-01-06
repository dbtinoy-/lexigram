"""Unit tests for InputSanitizer.

Adapted from lexigram-security/tests/unit/test_sanitizer.py.
Adds origin-guard assertion proving modules resolve to lexigram core.
"""

from __future__ import annotations

import importlib.util

import pytest

from lexigram.security.config import InputSanitizerConfig
from lexigram.security.sanitization.html import sanitize_html
from lexigram.security.sanitization.sanitizer import InputSanitizer


# ---------------------------------------------------------------------------
# Origin guard — proves core package is being exercised
# ---------------------------------------------------------------------------


class TestSanitizationModulesAreCore:
    """Verify sanitization modules resolve to lexigram core, not lexigram-security."""

    def test_sanitizer_module_is_core_package(self) -> None:
        spec = importlib.util.find_spec("lexigram.security.sanitization.sanitizer")
        assert spec is not None
        assert spec.origin is not None
        assert "lexigram-security" not in spec.origin, (
            f"Expected sanitizer to resolve to lexigram core, got: {spec.origin!r}"
        )

    def test_html_module_is_core_package(self) -> None:
        spec = importlib.util.find_spec("lexigram.security.sanitization.html")
        assert spec is not None
        assert spec.origin is not None
        assert "lexigram-security" not in spec.origin, (
            f"Expected html sanitizer to resolve to lexigram core, got: {spec.origin!r}"
        )

    def test_url_module_is_core_package(self) -> None:
        spec = importlib.util.find_spec("lexigram.security.sanitization.url")
        assert spec is not None
        assert spec.origin is not None
        assert "lexigram-security" not in spec.origin, (
            f"Expected url sanitizer to resolve to lexigram core, got: {spec.origin!r}"
        )

    def test_filename_module_is_core_package(self) -> None:
        spec = importlib.util.find_spec("lexigram.security.sanitization.filename")
        assert spec is not None
        assert spec.origin is not None
        assert "lexigram-security" not in spec.origin, (
            f"Expected filename sanitizer to resolve to lexigram core, got: {spec.origin!r}"
        )


# ---------------------------------------------------------------------------
# P2-html-sanitizer: nh3-based sanitize_html standalone function
# ---------------------------------------------------------------------------


def test_sanitize_html_blocks_malformed_script_tag() -> None:
    """P2-html-sanitizer: malformed <scr<script>ipt> must be neutralised."""
    result = sanitize_html("<scr<script>ipt>alert(1)</script>")
    assert "<script" not in result.lower()
    assert "</script>" not in result.lower()


def test_sanitize_html_strips_cdata() -> None:
    """P2-html-sanitizer: CDATA sections must be stripped."""
    result = sanitize_html("<![CDATA[<script>alert(1)</script>]]>")
    assert "<script" not in result.lower()
    assert "</script>" not in result.lower()


def test_sanitize_html_allows_safe_tags() -> None:
    """P2-html-sanitizer: safe tags in the default allowlist are preserved."""
    result = sanitize_html("<p>Hello <strong>world</strong></p>")
    assert "Hello" in result
    assert "world" in result


def test_sanitize_html_custom_allowed_tags() -> None:
    """P2-html-sanitizer: custom allowed_tags respected."""
    result = sanitize_html("<div><b>bold</b></div>", allowed_tags={"b"})
    assert "<b>" in result
    assert "<div>" not in result


def test_sanitize_html_strips_comments_by_default() -> None:
    """P2-html-sanitizer: HTML comments are stripped by default."""
    result = sanitize_html("<!-- secret --><p>visible</p>")
    assert "secret" not in result


def test_sanitize_html_keeps_comments_when_disabled() -> None:
    """P2-html-sanitizer: strip_comments=False retains HTML comments."""
    result = sanitize_html("<!-- keep me --><p>text</p>", strip_comments=False)
    assert "keep me" in result


class TestInputSanitizerAllowedTags:
    """Verify that InputSanitizer.strip_html respects InputSanitizerConfig.allowed_tags."""

    def test_strip_all_tags_by_default(self) -> None:
        """With no allowed_tags, every HTML tag is removed."""
        sanitizer = InputSanitizer()
        result = sanitizer.strip_html("<p>Hello <b>world</b></p>")
        assert result == "Hello world"

    def test_preserves_single_allowed_tag(self) -> None:
        """Tags listed in allowed_tags are kept; all others are stripped."""
        config = InputSanitizerConfig(allowed_tags={"b"})
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<p>Hello <b>world</b></p>")
        assert "<b>" in result
        assert "</b>" in result
        assert "<p>" not in result
        assert "</p>" not in result

    def test_preserves_multiple_allowed_tags(self) -> None:
        """Multiple tags in allowed_tags are all preserved."""
        config = InputSanitizerConfig(allowed_tags={"b", "i", "em"})
        sanitizer = InputSanitizer(config)
        html = "<div><b>bold</b> and <i>italic</i> and <em>emphasis</em></div>"
        result = sanitizer.strip_html(html)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<em>emphasis</em>" in result
        assert "<div>" not in result

    def test_allowed_tags_case_insensitive(self) -> None:
        """nh3 normalises tag names to lowercase in the output."""
        config = InputSanitizerConfig(allowed_tags={"b"})
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<P><B>text</B></P>")
        assert "<b>" in result
        assert "</b>" in result
        assert "<p>" not in result

    def test_closing_tags_of_allowed_elements_preserved(self) -> None:
        """Both opening and closing forms of an allowed tag survive."""
        config = InputSanitizerConfig(allowed_tags={"span"})
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<div><span>keep</span></div>")
        assert "<span>" in result
        assert "</span>" in result
        assert "<div>" not in result

    def test_empty_allowed_tags_strips_all(self) -> None:
        """Empty set of allowed_tags behaves like None (strip everything)."""
        config = InputSanitizerConfig(allowed_tags=set())
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<p><b>text</b></p>")
        assert result == "text"

    def test_html_comments_stripped_when_configured(self) -> None:
        """HTML comments are stripped when strip_comments=True (default)."""
        config = InputSanitizerConfig(allowed_tags={"b"})
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<!-- secret --><b>visible</b>")
        assert "secret" not in result
        assert "<b>visible</b>" in result

    def test_xss_payload_stripped_with_allowed_tags(self) -> None:
        """nh3 strips script elements entirely, including their text content."""
        config = InputSanitizerConfig(allowed_tags={"b", "i"})
        sanitizer = InputSanitizer(config)
        result = sanitizer.strip_html("<b>ok</b><script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert" not in result
        assert "<b>ok</b>" in result


class TestInputSanitizerSanitizeMethod:
    """Test the composite sanitize() method."""

    def test_sanitize_removes_script_tag(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("<script>alert('xss')</script>")
        assert "<script>" not in result

    def test_sanitize_removes_onclick_attribute(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize('<button onclick="evil()">Click</button>')
        assert "onclick" not in result

    def test_sanitize_url_blocks_javascript_scheme(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_url("javascript:alert(1)")
        assert result == ""

    def test_sanitize_url_allows_https(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_url("https://example.com")
        assert result == "https://example.com"

    def test_sanitize_filename_removes_path_traversal(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_filename("../../etc/passwd")
        assert ".." not in result

    def test_sanitize_header_value_removes_crlf(self) -> None:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_header_value("value\r\nX-Injected: evil")
        assert "\r" not in result
        assert "\n" not in result

    def test_sanitize_dict_sanitizes_all_strings(self) -> None:
        sanitizer = InputSanitizer()
        data = {"name": "<script>evil</script>hello", "age": 30}
        result = sanitizer.sanitize_dict(data)
        assert "<script>" not in result["name"]
        assert result["age"] == 30

    def test_is_safe_url_blocks_private_ip(self) -> None:
        sanitizer = InputSanitizer()
        assert sanitizer.is_safe_url_for_request("http://192.168.1.1/api") is False

    def test_is_safe_url_allows_public(self) -> None:
        sanitizer = InputSanitizer()
        assert sanitizer.is_safe_url_for_request("https://example.com") is True
