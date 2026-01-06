from __future__ import annotations

from typing import Any

from lexigram.search.validation.validator import SearchQueryValidator


def _get_validator() -> SearchQueryValidator:
    """Get the search query validator instance (sync for convenience)."""
    return SearchQueryValidator()


async def validate_search_query(query: str) -> tuple[bool, str | None]:
    validator = _get_validator()
    return validator.validate_query(query)


async def validate_search_filters(filters: Any) -> tuple[bool, str | None]:
    validator = _get_validator()
    return validator.validate_filters(filters)


async def validate_search_sort(sort: list[str] | None) -> tuple[bool, str | None]:
    validator = _get_validator()
    return validator.validate_sort(sort)


async def validate_index_name(name: str) -> tuple[bool, str | None]:
    validator = _get_validator()
    return validator.validate_index_name(name)


async def sanitize_search_query(query: str) -> str:
    validator = _get_validator()
    return validator.sanitize_query(query)


async def sanitize_search_filters(filters: Any) -> Any:
    validator = _get_validator()
    return validator.sanitize_filters(filters)
