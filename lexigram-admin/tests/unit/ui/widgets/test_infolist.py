from __future__ import annotations

from datetime import date

from lexigram.admin.ui.widgets.infolist import (
    InfolistEntry,
    InfolistEntryType,
    InfolistWidget,
)
from lexigram.ui import Element


class TestInfolistEntry:
    def test_construct_with_minimum_args(self) -> None:
        entry = InfolistEntry(name="name", label="Name")
        assert entry.name == "name"
        assert entry.label == "Name"
        assert entry.value is None

    def test_construct_with_value(self) -> None:
        entry = InfolistEntry(name="name", label="Name", value="John")
        assert entry.value == "John"


class TestInfolistWidget:
    def test_construct_with_entries(self) -> None:
        entries = [
            InfolistEntry(name="name", label="Name", value="John"),
            InfolistEntry(name="email", label="Email", value="john@example.com"),
        ]
        widget = InfolistWidget(entries=entries)
        assert len(widget.entries) == 2

    def test_render_returns_element(self) -> None:
        entries = [InfolistEntry(name="name", label="Name", value="John")]
        widget = InfolistWidget(entries=entries)
        element = widget.render()
        assert isinstance(element, Element)

    def test_render_empty_entries(self) -> None:
        widget = InfolistWidget(entries=[])
        output = str(widget.render())
        assert "No information available" in output

    def test_render_shows_labels(self) -> None:
        entries = [
            InfolistEntry(name="name", label="Name", value="John"),
            InfolistEntry(name="email", label="Email", value="john@example.com"),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "Name" in output
        assert "Email" in output

    def test_render_shows_values(self) -> None:
        entries = [InfolistEntry(name="name", label="Name", value="John")]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "John" in output

    def test_render_none_value_shows_dash(self) -> None:
        entries = [InfolistEntry(name="name", label="Name", value=None)]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "\u2014" in output

    def test_render_boolean_true(self) -> None:
        entries = [
            InfolistEntry(
                name="active",
                label="Active",
                value=True,
                type=InfolistEntryType.BOOLEAN,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "\u2713" in output

    def test_render_boolean_false(self) -> None:
        entries = [
            InfolistEntry(
                name="active",
                label="Active",
                value=False,
                type=InfolistEntryType.BOOLEAN,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "\u2717" in output

    def test_render_badge(self) -> None:
        entries = [
            InfolistEntry(
                name="status",
                label="Status",
                value="Active",
                type=InfolistEntryType.BADGE,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "Active" in output

    def test_render_date(self) -> None:
        entries = [
            InfolistEntry(
                name="created",
                label="Created",
                value=date(2026, 5, 28),
                type=InfolistEntryType.DATE,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "2026-05-28" in output

    def test_render_email(self) -> None:
        entries = [
            InfolistEntry(
                name="email",
                label="Email",
                value="test@example.com",
                type=InfolistEntryType.EMAIL,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "mailto:test@example.com" in output

    def test_render_url(self) -> None:
        entries = [
            InfolistEntry(
                name="website",
                label="Website",
                value="https://example.com",
                type=InfolistEntryType.URL,
            ),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "https://example.com" in output
        assert 'href="' in output

    def test_render_section_grouping(self) -> None:
        entries = [
            InfolistEntry(name="name", label="Name", section="Personal"),
            InfolistEntry(name="email", label="Email", section="Personal"),
            InfolistEntry(name="company", label="Company", section="Work"),
        ]
        widget = InfolistWidget(entries=entries)
        output = str(widget.render())
        assert "Personal" in output
        assert "Work" in output

    def test_columns_property(self) -> None:
        entries = [InfolistEntry(name="name", label="Name")]
        widget = InfolistWidget(entries=entries, columns=3)
        assert widget.columns == 3

    def test_columns_clamped(self) -> None:
        entries = [InfolistEntry(name="name", label="Name")]
        widget = InfolistWidget(entries=entries, columns=6)
        assert widget.columns == 4
