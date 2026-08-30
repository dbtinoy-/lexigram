"""Custom column renderers returning HTML strings must not silently produce
broken (escaped) cells — they should render escaped and warn once."""

from __future__ import annotations

from typing import Any

from lexigram.ui.columns import Column
from lexigram.ui import raw, render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable

class _FakeWarningLogger:
    """Stand-in for the structlog logger: read-only proxy otherwise."""

    def __init__(self) -> None:
        self.calls: list = []

    def warning(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class _HtmlStringColumn(Column):
    """Simulates the common app bug: render() returns a pre-built HTML string."""

    def __init__(self, name: str = "name") -> None:
        super().__init__(name)

    def render(self, value: Any, record: dict) -> Any:
        return f'<span class="badge">{value}</span>'


class _RawHtmlColumn(Column):
    """The correct fix: wrap the HTML string in raw() to mark intent."""

    def __init__(self, name: str = "name") -> None:
        super().__init__(name)

    def render(self, value: Any, record: dict) -> Any:
        return raw(f'<span class="badge">{value}</span>')


def _table_with(column: Column) -> str:
    return render_to_string(
        DataTable(
            columns=[column],
            data=[{"id": 1, "name": "Alice"}],
            resource_prefix="/admin/users",
        )
    )


def test_html_string_column_is_escaped_not_broken() -> None:
    """The browser must never see broken markup — escaped text is the safe
    default even when the developer made a mistake."""
    html = _table_with(_HtmlStringColumn())
    # The markup is escaped, so no real <span class="badge"> cell is emitted
    assert '&lt;span class="badge"&gt;Alice&lt;/span&gt;' in html
    assert '<span class="badge">Alice</span>' not in html


def test_raw_column_renders_intended_html() -> None:
    html = _table_with(_RawHtmlColumn())
    assert '<span class="badge">Alice</span>' in html


def test_html_string_column_warns_once(monkeypatch) -> None:
    import lexigram.ui.core.base as ui_base

    fake = _FakeWarningLogger()
    monkeypatch.setattr(ui_base, "logger", fake)
    # Distinct value so the dedup key differs from the other tests in this
    # module (the dedup set is module-global).
    render_to_string(
        DataTable(
            columns=[_HtmlStringColumn()],
            data=[{"id": 1, "name": "Bob"}],
            resource_prefix="/admin/users",
        )
    )
    render_to_string(
        DataTable(
            columns=[_HtmlStringColumn()],
            data=[{"id": 2, "name": "Bob"}],
            resource_prefix="/admin/users",
        )
    )
    # Deduplicated: one warning for this column, not one per cell render
    assert len(fake.calls) == 1
    assert "renderer_returned_html_string" in fake.calls[0][0][0]


def test_plain_text_column_does_not_warn(monkeypatch) -> None:
    import lexigram.ui.core.base as ui_base

    fake = _FakeWarningLogger()
    monkeypatch.setattr(ui_base, "logger", fake)
    _table_with(TextColumn("name"))
    assert fake.calls == []
