"""The ``lexigram.ui`` public import surface is stable across refactors.

The top-level package resolves names lazily through ``__getattr__``;
this suite pins the full ``__all__`` surface so re-organising the lazy
import map or the exports submodules cannot silently drop an export.
"""

from __future__ import annotations

import pytest

from lexigram import ui
from lexigram.ui import (  # noqa: F401 — lazy-surface smoke import
    Button,
    Card,
    Container,
    Form,
    Modal,
    Tabs,
)

_SAMPLE = ("Button", "Card", "Container", "Form", "Modal", "Tabs")


class TestPublicSurface:
    def test_sample_components_importable(self) -> None:
        """The named components resolve through the lazy surface."""
        for name in _SAMPLE:
            assert getattr(ui, name) is not None

    def test_every_all_name_resolves(self) -> None:
        """Every advertised name is reachable via the lazy import map."""
        for name in ui.__all__:
            assert getattr(ui, name) is not None, name

    def test_all_names_are_in_the_lazy_import_map(self) -> None:
        """Nothing in __all__ depends on an unknown lazy entry."""
        missing = [name for name in ui.__all__ if name not in ui._LAZY_IMPORTS]
        assert missing == []

    def test_dir_covers_public_surface(self) -> None:
        for name in ("Button", "Card", "Container", "Modal", "Tabs"):
            assert name in dir(ui)

    def test_lazy_getattr_caches_resolved_name(self) -> None:
        first = ui.Button
        second = ui.Button
        assert first is second

    def test_unknown_name_raises_attribute_error(self) -> None:
        assert not hasattr(ui, "DefinitelyNotAComponent")
        with pytest.raises(AttributeError):
            _ = ui.DefinitelyNotAComponent  # noqa: F841
