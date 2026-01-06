"""Search types — domain models and enums for search operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from lexigram.contracts.search.types import (
    DocumentData,
    IndexSettings,
    SearchFilters,
    SearchIndexResult,
)
from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False, frozen=True, slots=True)
class SearchResult(DomainModel, SearchIndexResult):
    """Single search result.

    Extends the canonical SearchIndexResult from contracts with DomainModel semantics.
    """

    id: str = Field(description="Unique document identifier")
    score: float = Field(description="Relevance score")
    data: dict[str, Any] = Field(description="Original document data")
    highlights: dict[str, str] | None = Field(
        default=None, description="Search term highlights"
    )


@dataclass(init=False)
class SearchResponse(DomainModel):
    """Search response with pagination."""

    results: list[SearchResult] = Field(description="List of search results")
    total: int = Field(description="Total number of matches")
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=20, description="Results per page")
    query: str = Field(default="", description="Original search query")
    took_ms: float | None = Field(default=None, description="Search execution time")
    facets: dict[str, Any] | None = Field(
        default=None, description="Search facets/aggregations"
    )


@dataclass(init=False)
class SearchQuery(DomainModel):
    """Search query parameters."""

    query: str = Field(description="Search term")
    filters: dict[str, Any] | None = Field(
        default=None, description="Search filter criteria"
    )
    page: int = Field(default=1, description="Target page number")
    per_page: int = Field(default=20, description="Target results per page")
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", description="Sort direction (asc/desc)")


# Backward-compatible alias used by external test utilities
RAGSearchResult = SearchResult


class SearchStrategy(StrEnum):
    """Search strategies."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    PHRASE = "phrase"


__all__ = [
    "DocumentData",
    "IndexSettings",
    "RAGSearchResult",
    "SearchFilters",
    "SearchIndexResult",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchStrategy",
]
