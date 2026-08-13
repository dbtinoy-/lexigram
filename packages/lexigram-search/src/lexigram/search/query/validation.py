"""Query Validation"""

from __future__ import annotations

from dataclasses import dataclass
import re
from re import Pattern
from typing import Any

from lexigram.search.config import SearchConfig
from lexigram.search.exceptions import SearchValidationError


@dataclass
class QueryValidationRule:
    """Query validation rule"""

    name: str
    pattern: Pattern[str] | None = None
    min_length: int | None = None
    max_length: int | None = None
    allowed_chars: str | None = None
    forbidden_words: list[str] | None = None
    required: bool = False


class QueryValidator:
    """Validates search queries"""

    def __init__(
        self,
        config: SearchConfig | None = None,
        rules: list[QueryValidationRule] | None = None,
    ):
        self.config = config or SearchConfig()
        self.rules = rules or self._default_rules()

    def _default_rules(self) -> list[QueryValidationRule]:
        """Get default validation rules"""
        return [
            QueryValidationRule(
                name="basic_query",
                min_length=1,
                max_length=1000,
                allowed_chars=r"[\w\s\-\+\*\?\(\)\[\]\{\}\"\~\:\&\^\|\!]+",
                forbidden_words=["<script", "javascript:", "onload", "onerror"],
            ),
        ]

    def add_rule(self, rule: QueryValidationRule) -> None:
        """Add a validation rule"""
        self.rules.append(rule)

    def validate_query(self, query: str) -> str:
        """Validate search query"""
        if not query:
            if any(rule.required for rule in self.rules):
                raise SearchValidationError("Query is required")
            return query

        for rule in self.rules:
            self._validate_against_rule(query, rule)

        return query

    def _validate_against_rule(self, query: str, rule: QueryValidationRule) -> None:
        """Validate query against a specific rule"""
        # Check minimum length
        if rule.min_length and len(query) < rule.min_length:
            raise SearchValidationError(
                f"Query too short (minimum {rule.min_length} characters)",
            )

        # Check maximum length
        if rule.max_length and len(query) > rule.max_length:
            raise SearchValidationError(
                f"Query too long (maximum {rule.max_length} characters)",
            )

        # Check allowed characters
        if rule.allowed_chars:
            pattern = re.compile(f"^[{rule.allowed_chars}]*$")
            if not pattern.match(query):
                raise SearchValidationError(
                    f"Query contains invalid characters. Allowed: {rule.allowed_chars}",
                )

        # Check pattern
        if rule.pattern and not rule.pattern.match(query):
            raise SearchValidationError(
                f"Query does not match required pattern: {rule.pattern.pattern}",
            )

        # Check forbidden words
        if rule.forbidden_words:
            query_lower = query.lower()
            for word in rule.forbidden_words:
                if word.lower() in query_lower:
                    raise SearchValidationError(
                        f"Query contains forbidden word: {word}"
                    )

    def sanitize_query(self, query: str) -> str:
        """Sanitize search query"""
        if not query:
            return query

        # Remove potentially dangerous characters
        query = re.sub(r"[<>]", "", query)

        # Trim whitespace
        query = query.strip()

        # Remove multiple spaces
        return re.sub(r"\s+", " ", query)

    def validate_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Validate search filters"""
        if not filters:
            return filters

        validated = {}

        for key, value in filters.items():
            # Basic key validation
            if not key or not isinstance(key, str):
                raise SearchValidationError(f"Invalid filter key: {key}")

            # Basic value validation
            if value is None:
                continue

            # Validate key format (no special characters that could be injection)
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", key):
                raise SearchValidationError(f"Invalid filter key format: {key}")

            validated[key] = value

        return validated

    def validate_pagination(self, limit: int, offset: int) -> tuple[int, int]:
        """Validate pagination parameters"""
        # Validate limit
        if limit < 1:
            limit = self.config.query.default_limit
        elif limit > self.config.query.max_limit:
            limit = self.config.query.max_limit

        # Validate offset
        offset = max(offset, 0)

        return limit, offset

    def validate_sort(self, sort: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate sort parameters"""
        if not sort:
            return sort

        validated = []

        for sort_item in sort:
            if not isinstance(sort_item, dict):
                raise SearchValidationError("Sort item must be a dictionary")

            # Should have exactly one key
            if len(sort_item) != 1:
                raise SearchValidationError("Sort item must have exactly one field")

            field, sort_config = next(iter(sort_item.items()))

            # Validate field name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", field):
                raise SearchValidationError(f"Invalid sort field name: {field}")

            # Validate sort config
            if not isinstance(sort_config, dict):
                raise SearchValidationError("Sort configuration must be a dictionary")

            order = sort_config.get("order", "asc")
            if order not in ("asc", "desc"):
                raise SearchValidationError(f"Invalid sort order: {order}")

            validated.append({field: sort_config})

        return validated


class QuerySanitizer:
    """Sanitizes search queries"""

    def __init__(self) -> None:
        self._dangerous_patterns = [
            re.compile(r"<[^>]*>", re.IGNORECASE),  # HTML tags
            re.compile(r"javascript:", re.IGNORECASE),  # JavaScript URLs
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
            re.compile(r"[\x00-\x1f\x7f-\x9f]"),  # Control characters
        ]

    def sanitize(self, query: str) -> str:
        """Sanitize search query"""
        if not query:
            return query

        # Apply dangerous pattern removal
        for pattern in self._dangerous_patterns:
            query = pattern.sub("", query)

        # Trim and normalize whitespace
        query = query.strip()
        query = re.sub(r"\s+", " ", query)

        # Escape special regex characters if they appear to be literal
        # This is conservative - only escape if not in common query syntax
        return self._escape_literals(query)

    def _escape_literals(self, query: str) -> str:
        """Escape literal special characters that aren't query syntax"""
        # Common query syntax patterns that should not be escaped
        query_patterns = [
            r"\*",  # Wildcard
            r"\?",  # Single char wildcard
            r"\(.*?\)",  # Grouping
            r"\[.*?\]",  # Character classes
            r'".*?"',  # Phrases
            r"~[0-9]*",  # Fuzzy
            r"\^[0-9]*",  # Boost
            r"\+",  # Required
            r"-",  # Prohibited
            r"&&|\|\|",  # Boolean operators
        ]

        # Find positions that are already in query syntax
        protected_positions: set[int] = set()
        for pattern in query_patterns:
            for match in re.finditer(pattern, query):
                protected_positions.update(range(match.start(), match.end()))

        # Escape unprotected special characters
        result = []
        for i, char in enumerate(query):
            if i in protected_positions:
                result.append(char)
            elif char in "[]{}()*+?.\\^$|":
                result.append(f"\\{char}")
            else:
                result.append(char)

        return "".join(result)


__all__ = ["QuerySanitizer", "QueryValidationRule", "QueryValidator"]
