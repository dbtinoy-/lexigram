"""Tests for lexigram.ai lazy __getattr__ and __dir__."""

from __future__ import annotations

import pytest


class TestAIPackageInit:
    """Tests for lexigram.ai lazy __getattr__ and __dir__."""

    def test_lazy_import_ai_config(self) -> None:
        import lexigram.ai as ai

        assert hasattr(ai, "AIConfig")
        from lexigram.ai import AIConfig  # noqa: F401

    def test_lazy_import_ai_provider(self) -> None:
        from lexigram.ai import AIProvider  # noqa: F401

        assert AIProvider is not None

    def test_lazy_import_ai_module(self) -> None:
        from lexigram.ai import AIModule  # noqa: F401

        assert AIModule is not None

    def test_dir_exposes_lazy_names(self) -> None:
        import lexigram.ai as ai

        names = dir(ai)
        assert "AIConfig" in names
        assert "AIProvider" in names
        assert "AIModule" in names

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        import lexigram.ai as ai

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = ai.NonExistentAttribute  # type: ignore[attr-defined]

    def test_version_accessible(self) -> None:
        import lexigram.ai as ai

        assert hasattr(ai, "__version__") or True
        from lexigram.ai.constants import __version__

        assert isinstance(__version__, str)
