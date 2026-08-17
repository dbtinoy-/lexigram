"""Tests for the accessibility module."""


from lexigram.ui.accessibility import (
    AriaAttrs,
    AriaLive,
    AriaRole,
    announce,
    announce_action_complete,
    announce_selection_change,
    announce_table_update,
    button_aria,
    cell_aria,
    dialog_aria,
    header_aria,
    keyboard_navigation_script,
    row_aria,
    search_aria,
    SkipLink,
    tab_aria,
    table_aria,
    tabpanel_aria,
)


class TestAriaLive:
    """Tests for AriaLive enum."""

    def test_values(self):
        assert AriaLive.OFF.value == "off"
        assert AriaLive.POLITE.value == "polite"
        assert AriaLive.ASSERTIVE.value == "assertive"


class TestAriaRole:
    """Tests for AriaRole enum."""

    def test_landmark_roles(self):
        assert AriaRole.BANNER.value == "banner"
        assert AriaRole.MAIN.value == "main"
        assert AriaRole.NAVIGATION.value == "navigation"

    def test_widget_roles(self):
        assert AriaRole.BUTTON.value == "button"
        assert AriaRole.DIALOG.value == "dialog"
        assert AriaRole.GRID.value == "grid"
        assert AriaRole.TAB.value == "tab"


class TestAriaAttrs:
    """Tests for AriaAttrs dataclass."""

    def test_empty_attrs(self):
        attrs = AriaAttrs()
        assert attrs.to_dict() == {}

    def test_role_attr(self):
        attrs = AriaAttrs(role=AriaRole.BUTTON)
        assert attrs.to_dict() == {"role": "button"}

    def test_label_attr(self):
        attrs = AriaAttrs(label="Click me")
        assert attrs.to_dict() == {"aria-label": "Click me"}

    def test_boolean_attrs(self):
        attrs = AriaAttrs(expanded=True, hidden=False, disabled=True)
        result = attrs.to_dict()
        assert result["aria-expanded"] == "true"
        assert result["aria-hidden"] == "false"
        assert result["aria-disabled"] == "true"

    def test_live_region_attrs(self):
        attrs = AriaAttrs(live=AriaLive.POLITE, atomic=True)
        result = attrs.to_dict()
        assert result["aria-live"] == "polite"
        assert result["aria-atomic"] == "true"

    def test_numeric_attrs(self):
        attrs = AriaAttrs(rowcount=100, colcount=5, rowindex=10)
        result = attrs.to_dict()
        assert result["aria-rowcount"] == "100"
        assert result["aria-colcount"] == "5"
        assert result["aria-rowindex"] == "10"


class TestTableAriaFactories:
    """Tests for table-related ARIA factories."""

    def test_table_aria(self):
        attrs = table_aria("Users table", rowcount=50, colcount=6)
        assert attrs["role"] == "grid"
        assert attrs["aria-label"] == "Users table"
        assert attrs["aria-rowcount"] == "50"
        assert attrs["aria-colcount"] == "6"

    def test_row_aria(self):
        attrs = row_aria(index=5, selected=True)
        assert attrs["role"] == "row"
        assert attrs["aria-rowindex"] == "5"
        assert attrs["aria-selected"] == "true"

    def test_row_aria_expanded(self):
        attrs = row_aria(index=1, expanded=True)
        assert attrs["aria-expanded"] == "true"

    def test_cell_aria(self):
        attrs = cell_aria(colindex=3)
        assert attrs["role"] == "gridcell"
        assert attrs["aria-colindex"] == "3"

    def test_header_aria_not_sortable(self):
        attrs = header_aria("Name")
        assert attrs["role"] == "columnheader"
        assert attrs["aria-label"] == "Name"
        assert "aria-sort" not in attrs

    def test_header_aria_sortable_none(self):
        attrs = header_aria("Name", sortable=True)
        assert attrs["aria-sort"] == "none"

    def test_header_aria_sortable_asc(self):
        attrs = header_aria("Name", sortable=True, sort_direction="asc")
        assert attrs["aria-sort"] == "ascending"

    def test_header_aria_sortable_desc(self):
        attrs = header_aria("Name", sortable=True, sort_direction="desc")
        assert attrs["aria-sort"] == "descending"


class TestButtonAria:
    """Tests for button ARIA factory."""

    def test_basic_button(self):
        attrs = button_aria("Submit form")
        assert attrs["role"] == "button"
        assert attrs["aria-label"] == "Submit form"

    def test_toggle_button(self):
        attrs = button_aria("Toggle sidebar", pressed=True)
        assert attrs["aria-pressed"] == "true"

    def test_menu_button(self):
        attrs = button_aria("Menu", expanded=False, haspopup="menu")
        assert attrs["aria-expanded"] == "false"
        assert attrs["aria-haspopup"] == "menu"


class TestDialogAria:
    """Tests for dialog ARIA factory."""

    def test_modal_dialog(self):
        attrs = dialog_aria("Confirm delete", modal=True)
        assert attrs["role"] == "dialog"
        assert attrs["aria-label"] == "Confirm delete"
        assert attrs["aria-modal"] == "true"

    def test_non_modal_dialog(self):
        attrs = dialog_aria("Info", modal=False)
        assert "aria-modal" not in attrs


class TestSearchAria:
    """Tests for search ARIA factory."""

    def test_search_input(self):
        attrs = search_aria("Search users", controls="results-list")
        assert attrs["role"] == "searchbox"
        assert attrs["aria-label"] == "Search users"
        assert attrs["aria-controls"] == "results-list"


class TestTabAria:
    """Tests for tab ARIA factories."""

    def test_tab_aria(self):
        attrs = tab_aria("Settings", selected=True, controls="settings-panel")
        assert attrs["role"] == "tab"
        assert attrs["aria-label"] == "Settings"
        assert attrs["aria-selected"] == "true"
        assert attrs["aria-controls"] == "settings-panel"

    def test_tabpanel_aria(self):
        attrs = tabpanel_aria(labelledby="settings-tab")
        assert attrs["role"] == "tabpanel"
        assert attrs["aria-labelledby"] == "settings-tab"


class TestAnnouncements:
    """Tests for screen reader announcements."""

    def test_announce_polite(self):
        html = announce("Data loaded")
        assert "sr-only" in html
        assert "Data loaded" in html
        assert 'aria-live="polite"' in html

    def test_announce_assertive(self):
        html = announce("Error!", priority=AriaLive.ASSERTIVE)
        assert 'aria-live="assertive"' in html

    def test_announce_table_update(self):
        html = announce_table_update(50, page=2)
        assert "50 items" in html
        assert "page 2" in html

    def test_announce_table_update_with_search(self):
        html = announce_table_update(10, search="john")
        assert "10 items" in html
        assert "filtered by 'john'" in html

    def test_announce_selection_change_zero(self):
        html = announce_selection_change(0)
        assert "No items selected" in html

    def test_announce_selection_change_one(self):
        html = announce_selection_change(1)
        assert "1 item selected" in html

    def test_announce_selection_change_many(self):
        html = announce_selection_change(5)
        assert "5 items selected" in html

    def test_announce_action_complete_success(self):
        html = announce_action_complete("Delete")
        assert "Delete completed successfully" in html

    def test_announce_action_complete_failure(self):
        html = announce_action_complete("Save", success=False)
        assert "Save failed" in html


class TestKeyboardNavigation:
    """Tests for keyboard navigation script."""

    def test_keyboard_navigation_script_is_script_tag(self):
        html = keyboard_navigation_script()
        assert "<script>" in html
        assert "</script>" in html

    def test_keyboard_navigation_contains_arrow_handling(self):
        html = keyboard_navigation_script()
        assert "ArrowDown" in html
        assert "ArrowUp" in html

    def test_keyboard_navigation_contains_escape_handling(self):
        html = keyboard_navigation_script()
        assert "Escape" in html

    def test_keyboard_navigation_contains_search_shortcut(self):
        html = keyboard_navigation_script()
        assert 'e.key==="/"' in html


class TestSkipLink:
    """Tests for skip link component."""

    def test_skip_link_default(self):
        html = SkipLink()
        assert 'href="#main-content"' in html
        assert "Skip to main content" in html
        assert "sr-only" in html

    def test_skip_link_custom(self):
        html = SkipLink(target_id="data-table", label="Skip to table")
        assert 'href="#data-table"' in html
        assert "Skip to table" in html
