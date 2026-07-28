"""Tests for engine validation module."""
from __future__ import annotations

import pytest

from lexigram.search.engine.validation import MAX_QUERY_LENGTH, validate_search_query


class TestValidateSearchQuery:
    """Tests for validate_search_query."""

    def test_valid_query(self) -> None:
        """Verify valid query returns True."""
        valid, error = validate_search_query("hello world")
        assert valid is True
        assert error is None

    def test_empty_string(self) -> None:
        """Verify empty string is valid (passes all checks)."""
        valid, error = validate_search_query("")
        assert valid is True
        assert error is None

    def test_non_string_input(self) -> None:
        """Verify non-string input returns False."""
        valid, error = validate_search_query(123)
        assert valid is False
        assert error == "Query must be a string"

    def test_none_input(self) -> None:
        """Verify None input returns False."""
        valid, error = validate_search_query(None)
        assert valid is False
        assert error == "Query must be a string"

    def test_query_too_long(self) -> None:
        """Verify query exceeding max length returns False."""
        long_query = "a" * (MAX_QUERY_LENGTH + 1)
        valid, error = validate_search_query(long_query)
        assert valid is False
        assert error == f"Query too long (max {MAX_QUERY_LENGTH} chars)"

    def test_max_length_boundary(self) -> None:
        """Verify query exactly at max length is valid."""
        exact_query = "a" * MAX_QUERY_LENGTH
        valid, error = validate_search_query(exact_query)
        assert valid is True
        assert error is None

    def test_script_tag_blocked(self) -> None:
        """Verify <script> pattern is blocked."""
        valid, error = validate_search_query("hello <script>alert('xss')</script>")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_javascript_protocol_blocked(self) -> None:
        """Verify javascript: protocol is blocked."""
        valid, error = validate_search_query("javascript:alert(1)")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_data_protocol_blocked(self) -> None:
        """Verify data: protocol is blocked."""
        valid, error = validate_search_query("data:text/html,<script>")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_vbscript_protocol_blocked(self) -> None:
        """Verify vbscript: protocol is blocked."""
        valid, error = validate_search_query("vbscript:msgbox")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_event_handler_blocked(self) -> None:
        """Verify on* event handler pattern is blocked."""
        valid, error = validate_search_query("onclick=alert(1)")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_sql_injection_blocked(self) -> None:
        """Verify SQL injection patterns are blocked."""
        valid, error = validate_search_query("; drop table users")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_case_insensitive_pattern_matching(self) -> None:
        """Verify suspicious patterns are matched case-insensitively."""
        valid, error = validate_search_query("<SCRIPT>alert(1)</SCRIPT>")
        assert valid is False
        assert error == "Query contains suspicious patterns"

    def test_normal_query_with_numbers(self) -> None:
        """Verify normal query with numbers passes."""
        valid, error = validate_search_query("search query 123")
        assert valid is True
        assert error is None

    def test_query_with_special_chars(self) -> None:
        """Verify query with allowed special characters passes."""
        valid, error = validate_search_query("hello-world foo_bar +baz")
        assert valid is True
        assert error is None
