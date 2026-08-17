"""JS-expression escaping regression tests for TabularView (Round 7 finding 33).

Record/group-derived values landing inside Alpine JS-string contexts must be
backslash-escaped by ``_js_str`` on top of ``el()``'s HTML attribute escaping:
the browser decodes HTML entities before Alpine compiles the attribute as
JavaScript, so a raw ``'`` in a record id could break out of the single-quoted
JS string (stored XSS in the authenticated admin table view).
"""

from __future__ import annotations

from lexigram.admin.actions.standard import DeleteBulkAction
from lexigram.admin.config import TableConfiguration
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui import render_to_string
from lexigram.ui.columns.types import TextColumn

LITMUS = "x');alert(1);//"


class HostileHeightConfig(TableConfiguration):
    """TableConfiguration whose density row height carries a hostile value."""

    @property
    def density_row_height(self) -> str:
        return "48px; background:url(evil)"


class CustomHeightConfig(TableConfiguration):
    """TableConfiguration with a valid custom density row height."""

    @property
    def density_row_height(self) -> str:
        return "60px"


def _render(config: TableConfiguration, data: list[dict]) -> str:
    dt = DataTable(
        config=config,
        data=data,
        resource_prefix=config.resource_prefix or "/admin/users",
    )
    return render_to_string(dt)


class TestRidInJsStringContexts:
    """Record ids interpolated into Alpine JS attributes stay enclosed."""

    def test_handleSelect_escapes_quote_breakout(self) -> None:
        config = TableConfiguration(
            columns=[TextColumn("name")],
            resource_prefix="/admin/users",
            bulk_actions=[DeleteBulkAction()],
        )
        html = _render(config, [{"id": LITMUS, "name": "A"}])

        assert "handleSelect" in html
        assert "\\&#x27;);alert(1);//" in html
        assert "handleSelect('x');alert(1);//" not in html

    def test_toggle_expand_sites_escape_quote_breakout(self) -> None:
        config = TableConfiguration(
            columns=[TextColumn("name")],
            resource_prefix="/admin/users",
            expandable_relationship="orders",
        )
        html = _render(config, [{"id": LITMUS, "name": "A"}])

        assert "toggleExpand" in html
        assert "expandedIds.includes" in html
        assert "aria-expanded" in html
        assert "\\&#x27;);alert(1);//" in html
        assert "toggleExpand('x');" not in html
        assert "expandedIds.includes('x');" not in html

    def test_focused_row_class_escapes_quote_breakout(self) -> None:
        config = TableConfiguration(columns=[TextColumn("name")])
        html = _render(config, [{"id": LITMUS, "name": "A"}])

        assert "focusedId" in html
        assert "focusedId === 'x');" not in html


class TestGroupNameInJsStringContexts:
    """Group names interpolated into Alpine JS attributes stay enclosed."""

    def test_toggle_group_escapes_quotes_backslashes_and_newlines(self) -> None:
        group_name = "x');alert(1)//\\nline2\nline3"
        config = TableConfiguration(columns=[TextColumn("name")], group_by="role")
        html = _render(config, [{"id": 1, "name": "A", "role": group_name}])

        assert "toggleGroup" in html
        assert "collapsedGroups.includes" in html
        assert "x&#x27;);alert(1)//" not in html
        assert "\\\\nline2" in html


class TestRowHeightValidation:
    """Hostile density row-height values fall back to the safe default."""

    def test_default_row_height_renders(self) -> None:
        config = TableConfiguration(columns=[TextColumn("name")])
        html = _render(config, [{"id": 1, "name": "A"}])

        assert "height: 48px;" in html

    def test_hostile_row_height_falls_back_to_default(self) -> None:
        config = HostileHeightConfig(columns=[TextColumn("name")])
        html = _render(config, [{"id": 1, "name": "A"}])

        assert "height: 48px;" in html
        assert "background:url" not in html

    def test_valid_custom_row_height_is_preserved(self) -> None:
        config = CustomHeightConfig(columns=[TextColumn("name")])
        html = _render(config, [{"id": 1, "name": "A"}])

        assert "height: 60px;" in html


class TestBenignRenderShapeIntact:
    """Existing shapes survive the wrapping (regression guard)."""

    def test_grouped_table_still_renders_groups(self) -> None:
        data = [
            {"id": 1, "name": "Alice", "role": "Admin"},
            {"id": 2, "name": "Bob", "role": "User"},
            {"id": 3, "name": "Charlie", "role": "Admin"},
        ]
        config = TableConfiguration(
            columns=[TextColumn("name"), TextColumn("role")], group_by="role"
        )
        html = _render(config, data)

        assert "(2)" in html
        assert "toggleGroup" in html
        assert "!collapsedGroups.includes" in html

    def test_expandable_detail_row_keeps_loading_placeholder(self) -> None:
        config = TableConfiguration(
            columns=[TextColumn("name")],
            resource_prefix="/admin/users",
            expandable_relationship="orders",
        )
        html = _render(config, [{"id": 7, "name": "A"}])

        assert "Loading relationship..." in html
        assert "hx-get" in html
