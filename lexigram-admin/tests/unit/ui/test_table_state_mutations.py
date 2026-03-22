"""
Unit tests for TableState mutation helpers.

Tests the new immutable mutation methods added to TableState:
- with_page()
- with_per_page()
- with_search()
- with_filter()
- without_filter()
- with_sort()
- with_view()
- with_layout()
- clear_filters()
- clear_sort()
- render_hidden_inputs()
"""

import pytest

from lexigram.ui.state import TableState


class TestTableStateMutationHelpers:
    """Tests for TableState mutation helper methods."""

    @pytest.fixture
    def state(self) -> TableState:
        """Create a base TableState for testing."""
        return TableState(
            search="test",
            page=2,
            per_page=20,
            sort_by="name",
            sort_order="asc",
            filters={"status": "active", "role": "admin"},
            view="tabular",
            layout="stack",
        )

    def test_with_page(self, state):
        """with_page should return new state with updated page."""
        new_state = state.with_page(5)

        # Original unchanged
        assert state.page == 2
        # New state updated
        assert new_state.page == 5
        # Cursor should be reset
        assert new_state.cursor is None
        # Other fields preserved
        assert new_state.search == "test"
        assert new_state.sort_by == "name"

    def test_with_per_page(self, state):
        """with_per_page should reset to page 1."""
        new_state = state.with_per_page(50)

        assert new_state.per_page == 50
        assert new_state.page == 1  # Reset
        assert new_state.cursor is None
        # Original unchanged
        assert state.per_page == 20
        assert state.page == 2

    def test_with_search(self, state):
        """with_search should reset to page 1."""
        new_state = state.with_search("new query")

        assert new_state.search == "new query"
        assert new_state.page == 1  # Reset
        # Original unchanged
        assert state.search == "test"

    def test_with_filter(self, state):
        """with_filter should add/update filter and reset page."""
        new_state = state.with_filter("category", "books")

        assert new_state.filters["category"] == "books"
        assert new_state.filters["status"] == "active"  # Preserved
        assert new_state.page == 1  # Reset
        # Original unchanged
        assert "category" not in state.filters

    def test_with_filter_updates_existing(self, state):
        """with_filter should update existing filter."""
        new_state = state.with_filter("status", "inactive")

        assert new_state.filters["status"] == "inactive"
        assert state.filters["status"] == "active"  # Original unchanged

    def test_without_filter(self, state):
        """without_filter should remove filter and reset page."""
        new_state = state.without_filter("status")

        assert "status" not in new_state.filters
        assert "role" in new_state.filters  # Other filters preserved
        assert new_state.page == 1  # Reset
        # Original unchanged
        assert "status" in state.filters

    def test_without_filter_nonexistent(self, state):
        """without_filter on nonexistent key should be safe."""
        new_state = state.without_filter("nonexistent")

        assert len(new_state.filters) == len(state.filters)

    def test_with_sort_new_column(self, state):
        """with_sort on new column should set ascending."""
        new_state = state.with_sort("email")

        assert new_state.sort_by == "email"
        assert new_state.sort_order == "asc"
        # Original unchanged
        assert state.sort_by == "name"

    def test_with_sort_toggle_direction(self, state):
        """with_sort on same column should toggle direction."""
        # First toggle: asc -> desc
        toggled = state.with_sort("name")
        assert toggled.sort_by == "name"
        assert toggled.sort_order == "desc"

        # Second toggle: desc -> asc
        toggled_again = toggled.with_sort("name")
        assert toggled_again.sort_order == "asc"

    def test_with_view(self, state):
        """with_view should update view type."""
        new_state = state.with_view("grid")

        assert new_state.view == "grid"
        assert state.view == "tabular"  # Original unchanged

    def test_with_layout(self, state):
        """with_layout should update layout type."""
        new_state = state.with_layout("sidebar")

        assert new_state.layout == "sidebar"
        assert state.layout == "stack"  # Original unchanged

    def test_clear_filters(self, state):
        """clear_filters should clear filters and search, reset page."""
        new_state = state.clear_filters()

        assert new_state.filters == {}
        assert new_state.search == ""
        assert new_state.page == 1
        # Other fields preserved
        assert new_state.sort_by == "name"
        assert new_state.view == "tabular"
        # Original unchanged
        assert state.filters == {"status": "active", "role": "admin"}
        assert state.search == "test"

    def test_clear_sort(self, state):
        """clear_sort should reset sort fields."""
        new_state = state.clear_sort()

        assert new_state.sort_by is None
        assert new_state.sort_order == "asc"  # Default
        # Original unchanged
        assert state.sort_by == "name"

    def test_method_chaining(self, state):
        """Mutation methods should be chainable."""
        new_state = (
            state.with_page(1)
            .with_search("query")
            .with_filter("category", "books")
            .with_sort("created_at")
        )

        assert new_state.page == 1
        assert new_state.search == "query"
        assert new_state.filters["category"] == "books"
        assert new_state.sort_by == "created_at"


class TestTableStateRenderHiddenInputs:
    """Tests for render_hidden_inputs method."""

    def test_render_hidden_inputs_basic(self):
        """render_hidden_inputs should create input elements."""
        state = TableState(
            search="test",
            sort_by="name",
            sort_order="asc",
            view="grid",
            layout="sidebar",
        )

        inputs = state.render_hidden_inputs()

        assert isinstance(inputs, list)
        assert len(inputs) > 0

    def test_render_hidden_inputs_only_non_defaults(self):
        """render_hidden_inputs should skip default values to keep clean."""
        state = TableState()  # All defaults

        inputs = state.render_hidden_inputs()

        # With all defaults, should have minimal inputs
        # (only non-default values are serialized)
        assert isinstance(inputs, list)

    def test_render_hidden_inputs_contains_state(self):
        """render_hidden_inputs should contain state values."""
        state = TableState(search="findme", page=3)

        inputs = state.render_hidden_inputs()
        inputs_html = "".join(str(i) for i in inputs)

        assert "findme" in inputs_html
        assert "page" in inputs_html
        assert '"3"' in inputs_html or 'value="3"' in inputs_html

    def test_render_hidden_inputs_data_state_marker(self):
        """Hidden inputs should have data-state marker."""
        state = TableState(search="test")

        inputs = state.render_hidden_inputs()
        inputs_html = "".join(str(i) for i in inputs)

        assert 'data-state="true"' in inputs_html
