"""Tests for accessibility utilities."""

import pytest

from lexigram.ui.accessibility import (
    AriaAttrs,
    AriaLive,
    AriaRole,
    table_aria,
    live_region_aria,
    button_aria,
    dialog_aria,
)


class TestAriaLive:
    """Tests for AriaLive enum."""

    def test_aria_live_values(self) -> None:
        """Test AriaLive enum values."""
        assert AriaLive.OFF.value == "off"
        assert AriaLive.POLITE.value == "polite"
        assert AriaLive.ASSERTIVE.value == "assertive"

    def test_aria_live_all_values(self) -> None:
        """Test all AriaLive values are defined."""
        values = {live.value for live in AriaLive}
        assert "off" in values
        assert "polite" in values
        assert "assertive" in values


class TestAriaRole:
    """Tests for AriaRole enum."""

    def test_aria_role_landmark_roles(self) -> None:
        """Test landmark role values."""
        assert AriaRole.BANNER.value == "banner"
        assert AriaRole.NAVIGATION.value == "navigation"
        assert AriaRole.MAIN.value == "main"
        assert AriaRole.COMPLEMENTARY.value == "complementary"
        assert AriaRole.CONTENTINFO.value == "contentinfo"
        assert AriaRole.SEARCH.value == "search"
        assert AriaRole.REGION.value == "region"

    def test_aria_role_widget_roles(self) -> None:
        """Test widget role values."""
        assert AriaRole.BUTTON.value == "button"
        assert AriaRole.CHECKBOX.value == "checkbox"
        assert AriaRole.DIALOG.value == "dialog"
        assert AriaRole.ALERTDIALOG.value == "alertdialog"
        assert AriaRole.GRID.value == "grid"
        assert AriaRole.LISTBOX.value == "listbox"
        assert AriaRole.MENU.value == "menu"
        assert AriaRole.TAB.value == "tab"
        assert AriaRole.TABLIST.value == "tablist"
        assert AriaRole.TABPANEL.value == "tabpanel"
        assert AriaRole.TOOLTIP.value == "tooltip"

    def test_aria_role_live_region_roles(self) -> None:
        """Test live region role values."""
        assert AriaRole.ALERT.value == "alert"
        assert AriaRole.LOG.value == "log"
        assert AriaRole.STATUS.value == "status"
        assert AriaRole.TIMER.value == "timer"


class TestAriaAttrs:
    """Tests for AriaAttrs dataclass."""

    def test_aria_attrs_empty(self) -> None:
        """Test empty AriaAttrs produces empty dict."""
        attrs = AriaAttrs()
        assert attrs.to_dict() == {}

    def test_aria_attrs_role(self) -> None:
        """Test role attribute."""
        attrs = AriaAttrs(role=AriaRole.BUTTON)
        result = attrs.to_dict()
        assert result["role"] == "button"

    def test_aria_attrs_label(self) -> None:
        """Test aria-label attribute."""
        attrs = AriaAttrs(label="Submit form")
        result = attrs.to_dict()
        assert result["aria-label"] == "Submit form"

    def test_aria_attrs_labelledby(self) -> None:
        """Test aria-labelledby attribute."""
        attrs = AriaAttrs(labelledby="title-id")
        result = attrs.to_dict()
        assert result["aria-labelledby"] == "title-id"

    def test_aria_attrs_describedby(self) -> None:
        """Test aria-describedby attribute."""
        attrs = AriaAttrs(describedby="desc-id")
        result = attrs.to_dict()
        assert result["aria-describedby"] == "desc-id"

    def test_aria_attrs_live(self) -> None:
        """Test aria-live attribute."""
        attrs = AriaAttrs(live=AriaLive.POLITE)
        result = attrs.to_dict()
        assert result["aria-live"] == "polite"

    def test_aria_attrs_atomic_true(self) -> None:
        """Test aria-atomic when True."""
        attrs = AriaAttrs(atomic=True)
        result = attrs.to_dict()
        assert result["aria-atomic"] == "true"

    def test_aria_attrs_atomic_false(self) -> None:
        """Test aria-atomic when False."""
        attrs = AriaAttrs(atomic=False)
        result = attrs.to_dict()
        assert result["aria-atomic"] == "false"

    def test_aria_attrs_busy_true(self) -> None:
        """Test aria-busy when True."""
        attrs = AriaAttrs(busy=True)
        result = attrs.to_dict()
        assert result["aria-busy"] == "true"

    def test_aria_attrs_controls(self) -> None:
        """Test aria-controls attribute."""
        attrs = AriaAttrs(controls="panel-id")
        result = attrs.to_dict()
        assert result["aria-controls"] == "panel-id"

    def test_aria_attrs_expanded_true(self) -> None:
        """Test aria-expanded when True."""
        attrs = AriaAttrs(expanded=True)
        result = attrs.to_dict()
        assert result["aria-expanded"] == "true"

    def test_aria_attrs_expanded_false(self) -> None:
        """Test aria-expanded when False."""
        attrs = AriaAttrs(expanded=False)
        result = attrs.to_dict()
        assert result["aria-expanded"] == "false"

    def test_aria_attrs_haspopup(self) -> None:
        """Test aria-haspopup attribute."""
        attrs = AriaAttrs(haspopup="menu")
        result = attrs.to_dict()
        assert result["aria-haspopup"] == "menu"

    def test_aria_attrs_hidden_true(self) -> None:
        """Test aria-hidden when True."""
        attrs = AriaAttrs(hidden=True)
        result = attrs.to_dict()
        assert result["aria-hidden"] == "true"

    def test_aria_attrs_invalid_true(self) -> None:
        """Test aria-invalid when True."""
        attrs = AriaAttrs(invalid=True)
        result = attrs.to_dict()
        assert result["aria-invalid"] == "true"

    def test_aria_attrs_pressed_true(self) -> None:
        """Test aria-pressed when True."""
        attrs = AriaAttrs(pressed=True)
        result = attrs.to_dict()
        assert result["aria-pressed"] == "true"

    def test_aria_attrs_selected_true(self) -> None:
        """Test aria-selected when True."""
        attrs = AriaAttrs(selected=True)
        result = attrs.to_dict()
        assert result["aria-selected"] == "true"

    def test_aria_attrs_disabled_true(self) -> None:
        """Test aria-disabled when True."""
        attrs = AriaAttrs(disabled=True)
        result = attrs.to_dict()
        assert result["aria-disabled"] == "true"

    def test_aria_attrs_current(self) -> None:
        """Test aria-current attribute."""
        attrs = AriaAttrs(current="page")
        result = attrs.to_dict()
        assert result["aria-current"] == "page"

    def test_aria_attrs_sort(self) -> None:
        """Test aria-sort attribute."""
        attrs = AriaAttrs(sort="ascending")
        result = attrs.to_dict()
        assert result["aria-sort"] == "ascending"

    def test_aria_attrs_rowcount(self) -> None:
        """Test aria-rowcount attribute."""
        attrs = AriaAttrs(rowcount=100)
        result = attrs.to_dict()
        assert result["aria-rowcount"] == "100"

    def test_aria_attrs_colcount(self) -> None:
        """Test aria-colcount attribute."""
        attrs = AriaAttrs(colcount=5)
        result = attrs.to_dict()
        assert result["aria-colcount"] == "5"

    def test_aria_attrs_rowindex(self) -> None:
        """Test aria-rowindex attribute."""
        attrs = AriaAttrs(rowindex=1)
        result = attrs.to_dict()
        assert result["aria-rowindex"] == "1"

    def test_aria_attrs_colindex(self) -> None:
        """Test aria-colindex attribute."""
        attrs = AriaAttrs(colindex=2)
        result = attrs.to_dict()
        assert result["aria-colindex"] == "2"

    def test_aria_attrs_multiple(self) -> None:
        """Test multiple attributes together."""
        attrs = AriaAttrs(
            role=AriaRole.DIALOG,
            label="Confirm delete",
            labelledby="dialog-title",
            expanded=True,
        )
        result = attrs.to_dict()
        assert result["role"] == "dialog"
        assert result["aria-label"] == "Confirm delete"
        assert result["aria-labelledby"] == "dialog-title"
        assert result["aria-expanded"] == "true"


class TestTableAria:
    """Tests for table_aria factory function."""

    def test_table_aria_basic(self) -> None:
        """Test basic table aria attributes."""
        result = table_aria("User data")
        assert result["role"] == "grid"
        assert result["aria-label"] == "User data"

    def test_table_aria_with_rowcount(self) -> None:
        """Test table aria with row count."""
        result = table_aria("User data", rowcount=100)
        assert result["aria-rowcount"] == "100"

    def test_table_aria_with_colcount(self) -> None:
        """Test table aria with column count."""
        result = table_aria("User data", colcount=5)
        assert result["aria-colcount"] == "5"

    def test_table_aria_sortable(self) -> None:
        """Test table aria with sortable flag."""
        result = table_aria("User data", sortable=True)
        # sortable is reserved for future use
        assert "aria-sortable" not in result


class TestLiveRegion:
    """Tests for live_region_aria factory function."""

    def test_live_region_polite(self) -> None:
        """Test polite live region."""
        result = live_region_aria()
        assert result["aria-live"] == "polite"
        assert result["aria-atomic"] == "true"

    def test_live_region_assertive(self) -> None:
        """Test assertive live region."""
        result = live_region_aria(AriaLive.ASSERTIVE)
        assert result["aria-live"] == "assertive"

    def test_live_region_off(self) -> None:
        """Test off live region."""
        result = live_region_aria(AriaLive.OFF)
        assert result["aria-live"] == "off"


class TestButtonAria:
    """Tests for button_aria factory function."""

    def test_button_aria_basic(self) -> None:
        """Test basic button aria."""
        result = button_aria("Submit")
        assert result["role"] == "button"

    def test_button_aria_expanded(self) -> None:
        """Test button with expanded state."""
        result = button_aria("Toggle", expanded=True)
        assert result["aria-expanded"] == "true"

    def test_button_aria_disabled(self) -> None:
        """Test button with disabled state."""
        result = button_aria("Submit", disabled=True)
        assert result["aria-disabled"] == "true"


class TestDialogAria:
    """Tests for dialog_aria factory function."""

    def test_dialog_aria_basic(self) -> None:
        """Test basic dialog aria."""
        result = dialog_aria("Confirm")
        assert result["role"] == "dialog"
        assert result["aria-label"] == "Confirm"

    def test_dialog_aria_modal(self) -> None:
        """Test modal dialog."""
        result = dialog_aria("Confirm", modal=True)
        assert result["aria-modal"] == "true"

