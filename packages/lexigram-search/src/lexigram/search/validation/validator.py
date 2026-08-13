from __future__ import annotations

import re
from typing import Any

from lexigram.di.decorators import singleton


@singleton
class SearchQueryValidator:
    """Validator for search queries, filters, and other parameters."""

    def __init__(self, max_query_length: int = 1000, max_filter_length: int = 500):
        self.max_query_length = max_query_length
        self.max_filter_length = max_filter_length

    def validate_query(self, query: str) -> tuple[bool, str | None]:
        """Validate a search query string."""
        if not query or not query.strip():
            return False, "Query cannot be empty"

        if len(query) > self.max_query_length:
            return False, f"Query too long (max {self.max_query_length} characters)"

        if any(ord(c) > 127 and ord(c) < 0x0500 for c in query) and any(
            c in "\u0456\u0430" for c in query
        ):
            return False, "Query contains suspicious unicode characters"

        suspicious_patterns = [
            (r"<script", "script"),
            (r"javascript:", "javascript:"),
            (r"vbscript:", "vbscript:"),
            (r"data:text/html", "data:"),
            (r"on\w+\s*=", "on"),
            (r"filters:", "filters:"),
            (r"facetFilters:", "facetFilters:"),
            (r"numericFilters:", "numericFilters:"),
            (r"tagFilters:", "tagFilters:"),
            (r"filter:", "filter:"),
            (r"sort:", "sort:"),
            (r"facets:", "facets:"),
            (r"filter_by:", "filter_by:"),
            (r"sort_by:", "sort_by:"),
            (r"facet_by:", "facet_by:"),
            (r'{"query":', '{"query":'),
            (r'{"match_all":', '{"match_all":'),
            (r'{"bool":', '{"bool":'),
            (r'{"script":', '{"script":'),
            (r'{"aggs":', '{"aggs":'),
            (r'{"size":', '{"size":'),
            (r'{"from":', '{"from":'),
            (r'{"range":', '{"range":'),
            (r";\s*drop", "; drop"),
            (r"--\s*drop", "drop"),
            (r";\s*select", "select"),
            (r"union\s+select", "union select"),
            (r"' OR '1'='1", "sql"),
            (r"OR '1'='1", "sql"),
            (r"\.\./\.\./", "../"),
            (r"\.\.\\\.\.\\", "..\\"),
            (r"/etc/passwd", "/etc/passwd"),
            (r"C:\\Windows", "C:\\Windows"),
            (r";\s*ls\s+-", "ls"),
            (r"\|\s*grep", "grep"),
            (r"`cat\s+/", "cat"),
            (r"\$\(rm\s+-", "rm"),
            (r";\s*ls\s+-la", "ls"),
        ]

        for pattern, name in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return (
                    False,
                    f"Query contains suspicious patterns: Query injection pattern: {name}. Input: {query}",
                )

        if len(query) > 20 and re.match(r"^[A-Za-z0-9+/=]+$", query):
            return False, "Query appears to contain encoded data"

        return True, None

    def validate_filters(self, filters: Any) -> tuple[bool, str | None]:
        """Validate search filters."""
        if filters is None:
            return True, None

        filters_str = str(filters)
        if len(filters_str) > self.max_filter_length:
            return False, "Filters too long"

        if '{"range":' in filters_str:
            return False, 'Filter injection pattern: {"range":'

        return True, None

    def validate_sort(self, sort: list[str] | None) -> tuple[bool, str | None]:
        """Validate sort parameters."""
        if not sort:
            return True, None

        for item in sort:
            if "_script" in item:
                return False, "Sort injection pattern: _script"

        return True, None

    def validate_index_name(self, name: str) -> tuple[bool, str | None]:
        """Validate an index name."""
        if not name:
            return False, "Index name cannot be empty"

        if len(name) > 255:
            return False, "Index name too long (max 255 characters)"

        if "/" in name or "\\" in name:
            return False, "Index name cannot contain path separators"

        if not re.match(r"^[a-zA-Z0-9\-_]+$", name):
            return (
                False,
                "Index name can only contain letters, numbers, hyphens, and underscores",
            )

        return True, None

    def sanitize_query(self, query: str) -> str:
        """Sanitize a search query."""
        if not query:
            return ""

        query = re.sub(
            r"<script.*?>.*?</script>",
            "",
            query,
            flags=re.IGNORECASE | re.DOTALL,
        )

        while re.search(r"<[^>]*>", query):
            query = re.sub(r"<[^>]*>", "", query)

        query = "".join(c for c in query if ord(c) >= 32 or c in "\n\r\t")

        query = re.sub(r"\*+", "*", query)

        return " ".join(query.split())

    def sanitize_filters(self, filters: Any) -> Any:
        """Sanitize search filters."""
        if isinstance(filters, dict):
            return {
                k: self.sanitize_query(v) if isinstance(v, str) else v
                for k, v in filters.items()
            }
        if isinstance(filters, str):
            return self.sanitize_query(filters)
        return filters
