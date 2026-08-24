"""Tests for lexigram.ai.di.factories."""

from __future__ import annotations


class TestDIFactories:
    """Tests for lexigram.ai.di.factories."""

    def test_factories_module_importable(self) -> None:
        import lexigram.ai.di.factories as factories  # noqa: F401

        assert factories is not None

    def test_factories_all_is_list(self) -> None:
        from lexigram.ai.di import factories

        assert isinstance(factories.__all__, list)
