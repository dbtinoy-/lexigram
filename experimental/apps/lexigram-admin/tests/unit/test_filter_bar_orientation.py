from lexigram.admin.ui.filters.types import SelectFilter
from lexigram.admin.ui.molecules.filter_bar import FilterBar


def test_filter_bar_vertical_and_horizontal():
    filters = [
        SelectFilter("status", options=["active", "inactive"]),
    ]

    fb_vert = FilterBar(
        filters=filters,
        current_values={},
        resource_prefix="/admin/users",
        display="vertical",
    )
    out_vert = str(fb_vert.render())
    assert "flex-col" in out_vert or "w-full" in out_vert
    assert 'hx-target="#table-data"' in out_vert

    fb_horiz = FilterBar(
        filters=filters,
        current_values={},
        resource_prefix="/admin/users",
        display="horizontal",
    )
    out_horiz = str(fb_horiz.render())
    assert "flex-row" in out_horiz or "flex-wrap" in out_horiz
    assert 'hx-target="#table-data"' in out_horiz


def test_filter_bar_mobile_toggle_exists():
    fb = FilterBar(
        filters=[SelectFilter("status", options=["active", "inactive"])],
        current_values={},
        resource_prefix="/admin/users",
    )
    html = str(fb.render())

    assert "x-data" in html
    assert "showFilters" in html


def test_filter_bar_mobile_toggle_visible_on_mobile_only():
    fb = FilterBar(
        filters=[SelectFilter("status", options=["active", "inactive"])],
        current_values={},
        resource_prefix="/admin/users",
    )
    html = str(fb.render())

    assert "md:hidden" in html


def test_filter_bar_xshow_showFilters():
    fb = FilterBar(
        filters=[SelectFilter("status", options=["active", "inactive"])],
        current_values={},
        resource_prefix="/admin/users",
    )
    html = str(fb.render())

    assert "x-show" in html or "showFilters" in html

