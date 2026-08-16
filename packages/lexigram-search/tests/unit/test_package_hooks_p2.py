"""P2 hook surface import verification for lexigram-search."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_search_hooks_root_module_exists() -> None:
    import lexigram.search
    from lexigram.search.hooks import (
        SearchIndexedHook,
        SearchQueryExecutedHook,
    )

    assert SearchIndexedHook.__name__ == "SearchIndexedHook"
    assert SearchQueryExecutedHook.__name__ == "SearchQueryExecutedHook"
    assert lexigram.search.SearchIndexedHook is SearchIndexedHook
    assert lexigram.search.SearchQueryExecutedHook is SearchQueryExecutedHook


def test_search_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.search.hooks import SearchIndexedHook, SearchQueryExecutedHook

    indexed = SearchIndexedHook(index_name="products", document_id="p1")
    queried = SearchQueryExecutedHook(
        index_name="products", query="blue shoes", result_count=5
    )

    assert is_dataclass(indexed)
    assert is_dataclass(queried)

    with pytest.raises(TypeError):
        SearchIndexedHook("products", "p1")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        indexed.index_name = "orders"  # type: ignore[misc]
