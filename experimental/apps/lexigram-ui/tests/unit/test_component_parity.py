"""Tests for cross-cutting shadcn parity, ARIA, Tabs, and FileUpload."""

from __future__ import annotations

from lexigram.ui.atoms.tooltip import Tooltip
from lexigram.ui.molecules.tabs import Tabs


class TestTabsContainer:
    def test_tabs_container(self) -> None:
        html = str(Tabs([("A", "a"), ("B", "b")]))
        assert 'role="tablist"' in html
        assert "bg-muted p-1 text-muted-foreground" in html


class TestTooltipAria:
    def test_tooltip_aria(self) -> None:
        html = str(Tooltip("More info"))
        assert 'role="tooltip"' in html


class TestFileUploadA11y:
    def test_file_upload_has_label_and_hint(self) -> None:
        from lexigram.ui.atoms.file_upload import FileUpload

        html = str(FileUpload(name="doc", label="Document"))
        assert 'for="' in html
        assert 'type="file"' in html
