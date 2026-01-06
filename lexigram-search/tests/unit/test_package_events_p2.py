"""P2 guardrail: lexigram-search must expose a canonical root events module."""

from __future__ import annotations


def test_search_events_root_module_exists() -> None:
    from lexigram.search.events import IndexingCompletedEvent, SearchExecutedEvent

    assert IndexingCompletedEvent.__name__ == "IndexingCompletedEvent"
    assert SearchExecutedEvent.__name__ == "SearchExecutedEvent"


def test_search_events_re_exported_from_package_root() -> None:
    import lexigram.search as search_pkg

    assert hasattr(search_pkg, "IndexingCompletedEvent")
    assert hasattr(search_pkg, "SearchExecutedEvent")
