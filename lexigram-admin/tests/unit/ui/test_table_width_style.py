from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.organisms.table.views.tabular import TabularView
from lexigram.ui.state import TableState


def test_filament_style_width_and_grow():
    cols = [
        TextColumn("a").width(4),
        TextColumn("b").width(3),
        TextColumn("c").width(6),
        TextColumn("d").grow(True),
        TextColumn("e").grow(True),
    ]

    config = TableConfiguration(columns=cols)
    state = TableState()
    data = [{"id": 1, "a": "A", "b": "B", "c": "C", "d": "D", "e": "E"}]

    tv = TabularView(data, config, state, total=1)
    html = render_to_string(tv.render())

    assert "width: 4.0rem" in html or "width: 4rem" in html
    assert "width: 3.0rem" in html or "width: 3rem" in html
    assert "width: 6.0rem" in html or "width: 6rem" in html

    assert "w-full" in html
    assert "min-w-0" in html


def test_table_height_is_viewport_aware():
    cols = [TextColumn("a")]
    config = TableConfiguration(columns=cols)
    state = TableState()
    data = [{"id": 1, "a": "A"}]

    tv = TabularView(data, config, state, total=1)
    html = render_to_string(tv.render())

    assert "max-height: min(70vh" in html
    assert "min-height: 200px" in html


def test_density_css_class_on_container():
    cols = [TextColumn("a")]
    config = TableConfiguration(columns=cols, density="compact")
    state = TableState()
    data = [{"id": 1, "a": "A"}]

    tv = TabularView(data, config, state, total=1)
    html = render_to_string(tv.render())

    assert "table-density-compact" in html


def test_density_row_height():
    cols = [TextColumn("a")]
    config = TableConfiguration(columns=cols, density="comfortable")
    state = TableState()
    data = [{"id": 1, "a": "A"}]

    tv = TabularView(data, config, state, total=1)
    html = render_to_string(tv.render())

    assert "height: 64px" in html
