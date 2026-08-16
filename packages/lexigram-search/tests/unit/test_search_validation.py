"""Tests for Search Query Validation"""

import pytest

from lexigram.search.validation import (
    SearchQueryValidator,
    sanitize_search_filters,
    sanitize_search_query,
    validate_index_name,
    validate_search_filters,
    validate_search_query,
    validate_search_sort,
)


class TestSearchQueryValidator:
    """Test the SearchQueryValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = SearchQueryValidator()
        assert validator.max_query_length == 1000
        assert validator.max_filter_length == 500

        validator = SearchQueryValidator(max_query_length=500, max_filter_length=200)
        assert validator.max_query_length == 500
        assert validator.max_filter_length == 200

    def test_validate_query_valid(self):
        """Test validating valid queries."""
        validator = SearchQueryValidator()

        # Valid queries
        assert validator.validate_query("test query") == (True, None)
        assert validator.validate_query("hello world") == (True, None)
        assert validator.validate_query("special chars: @#$%^&*()") == (True, None)

    def test_validate_query_invalid(self):
        """Test validating invalid queries."""
        validator = SearchQueryValidator()

        # Empty query
        assert validator.validate_query("") == (False, "Query cannot be empty")

        # Query too long
        long_query = "a" * 1001
        is_valid, error = validator.validate_query(long_query)
        assert not is_valid
        assert "Query too long" in error

        # Suspicious unicode
        assert validator.validate_query("іnvalid") == (
            False,
            "Query contains suspicious unicode characters",
        )

        # High entropy (base64-like)
        high_entropy = "VGhpcyBpcyBhIGJhc2U2NCBlbmNvZGU=" * 5
        assert validator.validate_query(high_entropy) == (
            False,
            "Query appears to contain encoded data",
        )

    def test_validate_query_injection_patterns(self):
        """Test detection of injection patterns."""
        validator = SearchQueryValidator()

        # Elasticsearch injection
        is_valid, error = validator.validate_query('{"query": {"match_all": {}}}')
        assert not is_valid
        assert "Query injection pattern" in error
        assert '{"query":' in error or '{"match_all":' in error

        # Algolia injection
        is_valid, error = validator.validate_query("filters:status:active")
        assert not is_valid
        assert "Query injection pattern: filters:" in error

        # Script injection
        is_valid, error = validator.validate_query("<script>alert('xss')</script>")
        assert not is_valid
        assert "Query injection pattern" in error
        assert "<script>alert('xss')</script>" in error

        # SQL injection
        is_valid, error = validator.validate_query("; DROP TABLE users;")
        assert not is_valid
        assert "Query injection pattern" in error
        assert "; drop" in error

    def test_validate_filters_valid(self):
        """Test validating valid filters."""
        validator = SearchQueryValidator()

        # Valid filters
        assert validator.validate_filters({"status": "active"}) == (True, None)
        assert validator.validate_filters(
            {"category": "electronics", "price": 100},
        ) == (True, None)
        assert validator.validate_filters(None) == (True, None)

    def test_validate_filters_invalid(self):
        """Test validating invalid filters."""
        validator = SearchQueryValidator()

        # Filters too long
        long_filters = {"key": "a" * 501}
        is_valid, error = validator.validate_filters(long_filters)
        assert not is_valid
        assert "Filters too long" in error

        # Filter injection
        is_valid, error = validator.validate_filters('{"range": {"price": {"gte": 0}}}')
        assert not is_valid
        assert "Filter injection pattern" in error
        assert '{"range":' in error

    def test_validate_sort_valid(self):
        """Test validating valid sort parameters."""
        validator = SearchQueryValidator()

        # Valid sort
        assert validator.validate_sort(["name:asc", "price:desc"]) == (True, None)
        assert validator.validate_sort(None) == (True, None)

    def test_validate_sort_invalid(self):
        """Test validating invalid sort parameters."""
        validator = SearchQueryValidator()

        # Sort injection
        is_valid, error = validator.validate_sort(["_script:asc"])
        assert not is_valid
        assert "Sort injection pattern" in error
        assert "_script" in error

    def test_validate_index_name_valid(self):
        """Test validating valid index names."""
        validator = SearchQueryValidator()

        # Valid names
        assert validator.validate_index_name("users") == (True, None)
        assert validator.validate_index_name("user_posts_2023") == (True, None)
        assert validator.validate_index_name("test-index") == (True, None)

    def test_validate_index_name_invalid(self):
        """Test validating invalid index names."""
        validator = SearchQueryValidator()

        # Invalid names
        assert validator.validate_index_name("") == (
            False,
            "Index name cannot be empty",
        )
        assert validator.validate_index_name("a" * 256) == (
            False,
            "Index name too long (max 255 characters)",
        )
        assert validator.validate_index_name("invalid@name") == (
            False,
            "Index name can only contain letters, numbers, hyphens, and underscores",
        )
        assert validator.validate_index_name("../escape") == (
            False,
            "Index name cannot contain path separators",
        )

    def test_sanitize_query(self):
        """Test query sanitization."""
        validator = SearchQueryValidator()

        # HTML removal
        assert (
            validator.sanitize_query("<script>alert('xss')</script>Hello world")
            == "Hello world"
        )

        # Control character removal
        assert validator.sanitize_query("Hello\x00world\x01") == "Helloworld"

        # Wildcard limiting
        assert validator.sanitize_query("test***query") == "test*query"

        # Whitespace normalization
        assert validator.sanitize_query("  hello   world  ") == "hello world"

    def test_sanitize_filters(self):
        """Test filter sanitization."""
        validator = SearchQueryValidator()

        # Dict filters
        filters = {"name": "<script>alert('xss')</script>John", "status": "active\x00"}
        sanitized = validator.sanitize_filters(filters)
        assert sanitized["name"] == "John"
        assert sanitized["status"] == "active"

        # String filters
        assert validator.sanitize_filters("<script>bad</script>filter") == "filter"


class TestValidationFunctions:
    """Test the module-level validation functions."""

    @pytest.mark.asyncio
    async def test_validate_search_query(self):
        """Test the validate_search_query function."""
        assert await validate_search_query("valid query") == (True, None)
        assert await validate_search_query("") == (False, "Query cannot be empty")

    @pytest.mark.asyncio
    async def test_validate_search_filters(self):
        """Test the validate_search_filters function."""
        assert await validate_search_filters({"status": "active"}) == (True, None)
        assert await validate_search_filters(None) == (True, None)

    @pytest.mark.asyncio
    async def test_validate_search_sort(self):
        """Test the validate_search_sort function."""
        assert await validate_search_sort(["name:asc"]) == (True, None)
        assert await validate_search_sort(None) == (True, None)

    @pytest.mark.asyncio
    async def test_validate_index_name_function(self):
        """Test the validate_index_name function."""
        assert await validate_index_name("valid_index") == (True, None)
        assert await validate_index_name("invalid@name") == (
            False,
            "Index name can only contain letters, numbers, hyphens, and underscores",
        )

    @pytest.mark.asyncio
    async def test_sanitize_search_query(self):
        """Test the sanitize_search_query function."""
        assert await sanitize_search_query("<b>bold</b> text") == "bold text"

    @pytest.mark.asyncio
    async def test_sanitize_search_filters(self):
        """Test the sanitize_search_filters function."""
        assert await sanitize_search_filters({"name": "<i>italic</i>"}) == {"name": "italic"}


class TestInjectionDetection:
    """Test comprehensive injection detection."""

    def test_elasticsearch_injection(self):
        """Test Elasticsearch-specific injection patterns."""
        validator = SearchQueryValidator()

        injection_queries = [
            '{"query": {"match_all": {}}}',
            '{"bool": {"must": []}}',
            '{"script": {"source": "doc[\'field\'].value"}}',
            '{"aggs": {"avg_price": {"avg": {"field": "price"}}}}',
            '{"size": 1000}',
            '{"from": 0}',
        ]

        for query in injection_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect injection in: {query}"
            assert "Query injection pattern" in error

    def test_algolia_injection(self):
        """Test Algolia-specific injection patterns."""
        validator = SearchQueryValidator()

        injection_queries = [
            "filters:status:active",
            "facetFilters:[['category:electronics']]",
            "numericFilters:price>=100",
            "tagFilters:[['tag1', 'tag2']]",
        ]

        for query in injection_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect injection in: {query}"
            assert "Query injection pattern" in error

    def test_meilisearch_injection(self):
        """Test MeiliSearch-specific injection patterns."""
        validator = SearchQueryValidator()

        injection_queries = [
            "filter:status = 'active'",
            "sort:price:desc,name:asc",
            "facets:['category', 'brand']",
        ]

        for query in injection_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect injection in: {query}"
            assert "Query injection pattern" in error

    def test_typesense_injection(self):
        """Test Typesense-specific injection patterns."""
        validator = SearchQueryValidator()

        injection_queries = [
            "filter_by:status:active",
            "sort_by:price:desc",
            "facet_by:category",
        ]

        for query in injection_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect injection in: {query}"
            assert "Query injection pattern" in error

    def test_xss_injection(self):
        """Test XSS injection patterns."""
        validator = SearchQueryValidator()

        xss_queries = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "vbscript:msgbox('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "onclick=alert('xss')",
        ]

        for query in xss_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect XSS in: {query}"
            assert "Query injection pattern" in error

    def test_sql_injection(self):
        """Test SQL injection patterns."""
        validator = SearchQueryValidator()

        sql_queries = [
            "; SELECT * FROM users;",
            "UNION SELECT password FROM users",
            "' OR '1'='1",
            "-- DROP TABLE users",
            "/* comment */ UNION SELECT",
        ]

        for query in sql_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect SQL injection in: {query}"
            assert "Query injection pattern" in error

    def test_path_traversal(self):
        """Test path traversal patterns."""
        validator = SearchQueryValidator()

        traversal_queries = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
        ]

        for query in traversal_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect path traversal in: {query}"
            assert "Query injection pattern" in error

    def test_command_injection(self):
        """Test command injection patterns."""
        validator = SearchQueryValidator()

        cmd_queries = [
            "; ls -la",
            "| grep password",
            "`cat /etc/passwd`",
            "$(rm -rf /)",
        ]

        for query in cmd_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Failed to detect command injection in: {query}"
            assert "Query injection pattern" in error


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_and_whitespace(self):
        """Test empty and whitespace handling."""
        validator = SearchQueryValidator()

        # Empty and whitespace queries
        assert validator.validate_query("") == (False, "Query cannot be empty")
        assert validator.validate_query("   ") == (False, "Query cannot be empty")
        assert validator.validate_query("\t\n") == (False, "Query cannot be empty")

    def test_unicode_handling(self):
        """Test unicode character handling."""
        validator = SearchQueryValidator()

        # Valid unicode
        assert validator.validate_query("café résumé naïve") == (True, None)

        # Suspicious homoglyphs
        assert validator.validate_query("іnvalid") == (
            False,
            "Query contains suspicious unicode characters",
        )
        assert validator.validate_query("аdmin") == (
            False,
            "Query contains suspicious unicode characters",
        )

        # Zero-width characters
        assert validator.validate_query("hidden\u200Btext") == (
            True,
            None,
        )  # Should be sanitized, not rejected

    def test_length_limits(self):
        """Test length limit enforcement."""
        validator = SearchQueryValidator(max_query_length=10, max_filter_length=5)

        # Query length
        assert validator.validate_query("short") == (True, None)
        is_valid, error = validator.validate_query("this is too long")
        assert not is_valid
        assert "Query too long" in error

        # Filter length
        assert validator.validate_filters("short") == (True, None)
        is_valid, error = validator.validate_filters("this filter is too long")
        assert not is_valid
        assert "Filters too long" in error

    def test_repetition_detection(self):
        """Test excessive repetition detection."""
        validator = SearchQueryValidator()

        # Normal repetition
        assert validator.validate_query("test test test") == (True, None)

        # Excessive repetition
        long_repetition = "test " * 201  # More than 1000 chars
        is_valid, error = validator.validate_query(long_repetition)
        assert not is_valid
        assert "Query too long" in error

    def test_mixed_injection_patterns(self):
        """Test queries with multiple injection patterns."""
        validator = SearchQueryValidator()

        # Query with multiple issues
        malicious_query = '{"query": {"match_all": {}}} <script>alert("xss")</script> ; DROP TABLE users;'
        is_valid, error = validator.validate_query(malicious_query)
        assert not is_valid
        # Should detect at least one pattern
        assert "suspicious patterns" in error
