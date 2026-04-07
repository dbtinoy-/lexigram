from lexigram.admin.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable


def test_layout_switcher_and_attrs():
    cols = [TextColumn("name")]
    data = [{"id": 1, "name": "Alice"}]

    dt = DataTable(
        columns=cols,
        data=data,
        resource_prefix="/admin/users",
        filter_options={"status": ["active", "inactive"]},
        layout_type="stack",
    )

    out = str(dt.render())
    # Layout switcher present
    assert "layout-switcher" in out
    # Buttons render as ActionButton content (icon buttons should be present)
    assert "aria-pressed" in out or "svg" in out
    # Layout buttons target the root container (for full table re-render on layout change)
    assert 'hx-target="#lexigram-table"' in out
    # Buttons should use baked URL approach, not hx-include
    assert 'hx-params="none"' in out

    # Sidebar injection
    dt2 = DataTable(
        columns=cols,
        data=data,
        resource_prefix="/admin/users",
        filter_options={"status": ["active", "inactive"]},
        layout_type="sidebar",
    )
    out2 = str(dt2.render())
    assert "layout-switcher" in out2
    assert out2.count('class="view-switcher') == 1
    # ActionButton uses icon-only SVGs; avoid brittle icon name checks, assert presence of icon-like output
    assert "aria-pressed" in out2 or "svg" in out2
