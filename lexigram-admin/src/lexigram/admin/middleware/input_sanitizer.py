"""Input sanitizer middleware for lexigram-admin.

Implements InputSanitizerProtocol from lexigram-contracts, providing
XSS payload stripping and HTML entity removal for user-supplied strings.
"""

from __future__ import annotations

import html
import re
from typing import Any

from lexigram.contracts.security import InputSanitizerProtocol

# Patterns that indicate an injection attempt or unsafe markup
_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onerror=, onclick=, etc.
    re.compile(r"<\s*iframe[\s\S]*?>", re.IGNORECASE),
    re.compile(r"<\s*object[\s\S]*?>", re.IGNORECASE),
    re.compile(r"<\s*embed[\s\S]*?>", re.IGNORECASE),
    re.compile(r"<\s*link[\s\S]*?>", re.IGNORECASE),
    re.compile(r"<\s*meta[\s\S]*?>", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),  # CSS expression()
    re.compile(r"data\s*:", re.IGNORECASE),  # data: URIs in attributes
]

# HTML tags — strip all; plain text fields must not carry markup
_HTML_TAG = re.compile(r"<[^>]+>")


class AdminInputSanitizer:
    """Concrete implementation of InputSanitizerProtocol for lexigram-admin.

    Applies defense-in-depth for user-supplied strings:
    1. Strips known XSS patterns (scripts, event handlers, dangerous URIs).
    2. Strips all remaining HTML tags.
    3. Unescapes and re-escapes HTML entities for consistent representation.
    """

    def sanitize(self, value: str) -> str:
        """Sanitize a single string value.

        Args:
            value: Raw input string.

        Returns:
            The sanitized string with XSS vectors removed.
        """
        # Step 1 — strip dangerous patterns
        result = value
        for pattern in _DANGEROUS_PATTERNS:
            result = pattern.sub("", result)

        # Step 2 — strip residual HTML tags
        result = _HTML_TAG.sub("", result)

        # Step 3 — unescape then re-escape to normalize entities
        result = html.escape(html.unescape(result), quote=True)

        return result.strip()

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize all string leaf values in a mapping.

        Args:
            data: Dictionary whose string leaf values will be sanitized.

        Returns:
            A new dictionary with all string leaf values sanitized.
            Non-string values are passed through unchanged.
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.sanitize(value)
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def sanitize_header_value(self, value: str) -> str:
        """Strip CRLF characters from an HTTP header value to prevent header injection.

        Args:
            value: Raw header value string.

        Returns:
            The value with CR and LF characters removed.
        """
        return re.sub(r"[\r\n]", "", value)

    def is_safe_url_for_request(self, url: str) -> bool:
        """Return False if the URL targets a private or reserved IP range (SSRF guard).

        Delegates to the single shared primitive in ``lexigram.contracts``.

        Args:
            url: Fully-qualified URL to evaluate.

        Returns:
            True if the URL is considered safe to request, False otherwise.
        """
        from lexigram.contracts.security import is_safe_url_for_request

        return is_safe_url_for_request(url)


# Verify structural compliance at import time
assert isinstance(AdminInputSanitizer(), InputSanitizerProtocol)  # noqa: S101  # import-time protocol conformance

__all__ = ["AdminInputSanitizer"]
