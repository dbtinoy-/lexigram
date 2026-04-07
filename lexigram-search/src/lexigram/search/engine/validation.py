from __future__ import annotations

import re

MAX_QUERY_LENGTH = 1000


def validate_search_query(query: str) -> tuple[bool, str | None]:
    """Validate a search query string."""
    if not isinstance(query, str):
        return False, "Query must be a string"
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} chars)"

    suspicious_patterns = [
        r"<script",
        r"javascript:",
        r"data:",
        r"vbscript:",
        r"on\w+\s*=",
        r";\s*(select|insert|update|delete|drop)",
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Query contains suspicious patterns"

    return True, None
