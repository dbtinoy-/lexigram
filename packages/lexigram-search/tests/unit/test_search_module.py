"""Tests for search module."""

import pytest
from lexigram.search import SearchModule
from lexigram.di.module import DynamicModule


class TestSearchModule:
    def test_search_module_exists(self) -> None:
        assert SearchModule is not None

    def test_configure_requires_config(self) -> None:
        with pytest.raises(ValueError, match="requires a SearchConfig"):
            SearchModule.configure(None)
