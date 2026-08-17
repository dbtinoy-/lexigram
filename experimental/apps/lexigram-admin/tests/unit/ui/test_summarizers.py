"""Tests for per-column table summarizers."""

from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.organisms.table.views.summarizers import compute_summaries
from lexigram.admin.ui.organisms.table.views.tabular import TabularView
from lexigram.ui import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.ui.state import TableState

ROWS = [
    {"id": 1, "price": "10", "name": "A"},
    {"id": 2, "price": "15.5", "name": "B"},
    {"id": 3, "price": "", "name": ""},
]


def test_compute_summaries_sum():
    cols = [TextColumn("price").summarizer("sum"), TextColumn("name")]
    out = compute_summaries(ROWS, cols)
    assert out["price"] == "Sum 25.5"
    assert "name" not in out


def test_compute_summaries_average():
    cols = [TextColumn("price").summarizer("average")]
    out = compute_summaries(ROWS, cols)
    assert out["price"] == "Average 12.75"


def test_compute_summaries_count_skips_empty():
    cols = [TextColumn("name").summarizer("count")]
    out = compute_summaries(ROWS, cols)
    assert out["name"] == "Count 2"


def test_compute_summaries_range():
    cols = [TextColumn("price").summarizer("range")]
    out = compute_summaries(ROWS, cols)
    assert out["price"] == "Range 10 - 15.5"


def test_compute_summaries_skips_non_numeric_for_sum():
    cols = [TextColumn("name").summarizer("sum")]
    out = compute_summaries(ROWS, cols)
    assert out == {}


def test_compute_summaries_empty_data():
    cols = [TextColumn("price").summarizer("sum")]
    assert compute_summaries([], cols) == {}


def test_tabular_view_renders_computed_footer():
    cols = [TextColumn("price").summarizer("sum"), TextColumn("name")]
    config = TableConfiguration(columns=cols)
    view = TabularView(data=ROWS, config=config, state=TableState())
    html = render_to_string(view.render())
    assert "<tfoot" in html
    assert "Sum 25.5" in html


def test_tabular_view_no_footer_without_summarizers():
    cols = [TextColumn("price"), TextColumn("name")]
    config = TableConfiguration(columns=cols)
    view = TabularView(data=ROWS, config=config, state=TableState())
    html = render_to_string(view.render())
    assert "<tfoot" not in html


def test_tabular_view_explicit_summary_takes_precedence():
    cols = [TextColumn("price").summarizer("sum"), TextColumn("name")]
    config = TableConfiguration(columns=cols)
    view = TabularView(
        data=ROWS,
        config=config,
        state=TableState(),
        summary={"price": "Custom 99"},
    )
    html = render_to_string(view.render())
    assert "Custom 99" in html
    assert "Sum 25.5" not in html
