"""Tests for AdminInputSanitizer."""

from __future__ import annotations

import pytest

from lexigram.admin.middleware.input_sanitizer import AdminInputSanitizer
from lexigram.contracts.security import InputSanitizerProtocol


class TestAdminInputSanitizerProtocol:
    def test_implements_protocol(self) -> None:
        assert isinstance(AdminInputSanitizer(), InputSanitizerProtocol)


class TestAdminInputSanitizerSanitize:
    @pytest.fixture
    def sanitizer(self) -> AdminInputSanitizer:
        return AdminInputSanitizer()

    # -- Clean input ----------------------------------------------------------

    def test_clean_string_unchanged(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.sanitize("Hello world") == "Hello world"

    def test_empty_string(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.sanitize("") == ""

    def test_whitespace_stripped(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.sanitize("  hello  ") == "hello"

    # -- Script tags ----------------------------------------------------------

    def test_strips_script_tag(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize("<script>alert('xss')</script>")
        assert "<script" not in result
        assert "alert" not in result

    def test_strips_script_tag_with_attributes(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        result = sanitizer.sanitize("<script type='text/javascript'>evil()</script>")
        assert "<script" not in result

    def test_strips_script_tag_multiline(self, sanitizer: AdminInputSanitizer) -> None:
        payload = "<script>\nvar x=1;\nalert(x);\n</script>"
        result = sanitizer.sanitize(payload)
        assert "<script" not in result
        assert "alert" not in result

    # -- JavaScript URI -------------------------------------------------------

    def test_strips_javascript_uri(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize("javascript:alert(1)")
        assert "javascript" not in result.lower()

    def test_strips_javascript_uri_with_spaces_before_colon(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        """javascript\\s*: pattern handles spaces between the keyword and colon."""
        result = sanitizer.sanitize("javascript   : alert(1)")
        assert "javascript" not in result.lower()

    # -- Event handlers -------------------------------------------------------

    def test_strips_onerror_handler(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize("<img src=x onerror=alert(1)>")
        assert "onerror" not in result

    def test_strips_onclick_handler(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize('<button onclick="evil()">click</button>')
        assert "onclick" not in result

    # -- Dangerous elements ---------------------------------------------------

    def test_strips_iframe(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize('<iframe src="http://evil.com"></iframe>')
        assert "<iframe" not in result.lower()

    def test_strips_object_tag(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize('<object data="evil.swf"></object>')
        assert "<object" not in result.lower()

    def test_strips_embed_tag(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize('<embed src="evil.swf">')
        assert "<embed" not in result.lower()

    # -- HTML entities --------------------------------------------------------

    def test_escapes_standalone_lt_operator(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        """A bare < not followed by > is not a tag — it gets entity-encoded."""
        result = sanitizer.sanitize("5 < 10")
        assert "<" not in result
        assert "&lt;" in result

    def test_tag_like_content_stripped_entirely(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        """< b > looks like an HTML tag and is stripped by the tag regex."""
        result = sanitizer.sanitize("a < b > c")
        assert "<" not in result
        assert ">" not in result

    def test_escapes_ampersand(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize("a & b")
        assert "&amp;" in result

    def test_escapes_quotes(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize('"quoted"')
        assert "&quot;" in result

    def test_normalizes_encoded_entities(self, sanitizer: AdminInputSanitizer) -> None:
        # Double-encoded entity should be properly normalized
        result = sanitizer.sanitize("&amp;lt;")
        assert "&amp;" in result

    # -- Residual HTML tags ---------------------------------------------------

    def test_strips_arbitrary_html_tag(self, sanitizer: AdminInputSanitizer) -> None:
        result = sanitizer.sanitize("<b>bold</b>")
        assert "<b>" not in result
        assert "</b>" not in result

    def test_safe_text_preserved_after_tag_strip(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        result = sanitizer.sanitize("<b>hello</b> world")
        assert "hello" in result
        assert "world" in result


class TestAdminInputSanitizerSanitizeDict:
    @pytest.fixture
    def sanitizer(self) -> AdminInputSanitizer:
        return AdminInputSanitizer()

    def test_sanitizes_string_values(self, sanitizer: AdminInputSanitizer) -> None:
        data = {"name": "<script>evil()</script>John"}
        result = sanitizer.sanitize_dict(data)
        assert "<script" not in result["name"]

    def test_non_string_values_unchanged(self, sanitizer: AdminInputSanitizer) -> None:
        data: dict = {"count": 42, "active": True, "ratio": 3.14}
        result = sanitizer.sanitize_dict(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["ratio"] == 3.14

    def test_nested_dict_sanitized(self, sanitizer: AdminInputSanitizer) -> None:
        data = {"user": {"bio": "<script>xss</script>hello"}}
        result = sanitizer.sanitize_dict(data)
        assert "<script" not in result["user"]["bio"]
        assert "hello" in result["user"]["bio"]

    def test_list_string_values_sanitized(self, sanitizer: AdminInputSanitizer) -> None:
        data = {"tags": ["<b>tag1</b>", "normal", "<em>tag2</em>"]}
        result = sanitizer.sanitize_dict(data)
        for tag in result["tags"]:
            assert "<b>" not in tag
            assert "<em>" not in tag

    def test_list_non_string_values_unchanged(
        self, sanitizer: AdminInputSanitizer
    ) -> None:
        data = {"ids": [1, 2, 3]}
        result = sanitizer.sanitize_dict(data)
        assert result["ids"] == [1, 2, 3]

    def test_returns_new_dict(self, sanitizer: AdminInputSanitizer) -> None:
        data = {"key": "value"}
        result = sanitizer.sanitize_dict(data)
        assert result is not data

    def test_empty_dict(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.sanitize_dict({}) == {}

    def test_clean_data_unchanged_values(self, sanitizer: AdminInputSanitizer) -> None:
        data = {"first": "Alice", "last": "Smith"}
        result = sanitizer.sanitize_dict(data)
        assert result["first"] == "Alice"
        assert result["last"] == "Smith"


class TestAdminInputSanitizerUrlSafety:
    @pytest.fixture
    def sanitizer(self) -> AdminInputSanitizer:
        return AdminInputSanitizer()

    def test_blocks_loopback_literal(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.is_safe_url_for_request("http://127.0.0.1/admin") is False

    def test_blocks_private_literal(self, sanitizer: AdminInputSanitizer) -> None:
        assert sanitizer.is_safe_url_for_request("http://192.168.1.5/api") is False
        assert sanitizer.is_safe_url_for_request("http://10.0.0.1/") is False

    def test_allows_public_hostname(
        self, sanitizer: AdminInputSanitizer, monkeypatch
    ) -> None:
        import ipaddress

        from lexigram.contracts.security import url_safety as contracts_url_safety

        monkeypatch.setattr(
            contracts_url_safety,
            "resolve_hostname",
            lambda _: [ipaddress.ip_address("93.184.216.34")],
        )
        assert sanitizer.is_safe_url_for_request("https://example.com/") is True
