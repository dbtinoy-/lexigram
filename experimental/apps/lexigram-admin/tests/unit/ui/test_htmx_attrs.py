"""
Unit tests for the HTMXAttrs builder.

Tests the htmx_attrs.py module which provides:
- HTMXAttrsBuilder for building HTMX attributes
- HTMXAttrs factory with convenience methods
"""

import pytest

from lexigram.ui import HTMXAttrs, HTMXAttrsBuilder
from lexigram.ui.core.zones import Zones
from lexigram.ui.state import TableState


class TestHTMXAttrsBuilder:
    """Tests for HTMXAttrsBuilder class."""

    @pytest.fixture
    def state(self) -> TableState:
        """Create a basic TableState for testing."""
        return TableState(
            search="test",
            page=2,
            per_page=20,
            sort_by="name",
            sort_order="asc",
        )

    def test_full_refresh_attrs(self, state):
        """Full refresh should target TABLE zone with outerHTML."""
        builder = HTMXAttrsBuilder(
            action="full_refresh",
            state=state,
            resource_prefix="/admin/users",
        )
        attrs = builder.build()

        assert attrs["hx-target"] == Zones.TABLE.selector
        assert attrs["hx-swap"] == "outerHTML"
        assert attrs["hx-params"] == "none"
        assert attrs["hx-push-url"] == "true"
        assert "hx-get" in attrs
        # State should be baked into URL
        assert "search=test" in attrs["hx-get"]
        assert "page=2" in attrs["hx-get"]

    def test_data_refresh_attrs(self, state):
        """Data refresh should target DATA zone with innerHTML."""
        builder = HTMXAttrsBuilder(
            action="data_refresh",
            state=state,
            resource_prefix="/admin/users",
        )
        attrs = builder.build()

        assert attrs["hx-target"] == Zones.DATA.selector
        assert attrs["hx-swap"] == "innerHTML"
        assert attrs["hx-select"] == Zones.DATA.selector  # Extract only DATA
        assert attrs["hx-params"] == "none"
        assert "hx-get" in attrs

    def test_modal_attrs(self, state):
        """Modal action should target MODAL zone."""
        builder = HTMXAttrsBuilder(
            action="modal",
            state=state,
            resource_prefix="/admin/users/1/edit",
        )
        attrs = builder.build()

        assert attrs["hx-target"] == Zones.MODAL.selector
        assert attrs["hx-swap"] == "innerHTML"
        assert attrs["hx-push-url"] == "false"

    def test_slide_over_attrs(self, state):
        """Slide-over action should target SLIDE_OVER zone."""
        builder = HTMXAttrsBuilder(
            action="slide_over",
            state=state,
            resource_prefix="/admin/users/create",
        )
        attrs = builder.build()

        assert attrs["hx-target"] == Zones.SLIDE_OVER.selector
        assert attrs["hx-swap"] == "innerHTML"
        assert attrs["hx-push-url"] == "false"

    def test_extra_params_included(self, state):
        """Extra params should be included in URL."""
        builder = HTMXAttrsBuilder(
            action="data_refresh",
            state=state,
            resource_prefix="/admin/users",
            extra_params={"custom": "value"},
        )
        attrs = builder.build()

        assert "custom=value" in attrs["hx-get"]

    def test_push_url_override(self, state):
        """push_url parameter should override default."""
        builder = HTMXAttrsBuilder(
            action="full_refresh",
            state=state,
            resource_prefix="/admin/users",
            push_url=False,
        )
        attrs = builder.build()

        assert attrs["hx-push-url"] == "false"

    def test_confirm_message(self, state):
        """Confirm message should be added to attrs."""
        builder = HTMXAttrsBuilder(
            action="data_refresh",
            state=state,
            resource_prefix="/admin/users",
            confirm_message="Are you sure?",
        )
        attrs = builder.build()

        assert attrs["hx-confirm"] == "Are you sure?"

    def test_invalid_action_raises(self, state):
        """Invalid action type should raise ValueError."""
        builder = HTMXAttrsBuilder(
            action="invalid",
            state=state,
            resource_prefix="/admin/users",
        )
        with pytest.raises(ValueError, match="Unknown action type"):
            builder.build()


class TestHTMXAttrs:
    """Tests for HTMXAttrs factory class."""

    @pytest.fixture
    def state(self) -> TableState:
        """Create a basic TableState for testing."""
        return TableState(search="query", page=1)

    @pytest.fixture
    def full_state(self) -> TableState:
        """Create a full TableState with filters and sort."""
        return TableState(
            search="hello",
            page=3,
            per_page=50,
            sort_by="name",
            sort_order="desc",
            filters={"status": "active"},
            view="tabular",
            layout="stack",
        )

    def test_for_full_refresh(self, state):
        """for_full_refresh should generate correct attrs."""
        attrs = HTMXAttrs.for_full_refresh(state, "/admin/users")

        assert attrs["hx-target"] == Zones.TABLE.selector
        assert attrs["hx-swap"] == "outerHTML"
        assert "hx-get" in attrs
        assert "search=query" in attrs["hx-get"]

    def test_for_data_refresh(self, state):
        """for_data_refresh should generate correct attrs."""
        attrs = HTMXAttrs.for_data_refresh(state, "/admin/users")

        assert attrs["hx-target"] == Zones.DATA.selector
        assert attrs["hx-select"] == Zones.DATA.selector
        assert "hx-get" in attrs

    def test_for_modal(self):
        """for_modal should generate correct attrs."""
        attrs = HTMXAttrs.for_modal("/admin/users/1/view")

        assert attrs["hx-get"] == "/admin/users/1/view"
        assert attrs["hx-target"] == Zones.MODAL.selector
        assert attrs["hx-push-url"] == "false"

    def test_for_slide_over(self):
        """for_slide_over should generate correct attrs."""
        attrs = HTMXAttrs.for_slide_over("/admin/users/create")

        assert attrs["hx-get"] == "/admin/users/create"
        assert attrs["hx-target"] == Zones.SLIDE_OVER.selector
        assert attrs["hx-push-url"] == "false"

    def test_for_delete(self):
        """for_delete should generate correct attrs."""
        attrs = HTMXAttrs.for_delete("/admin/users/123")

        assert attrs["hx-delete"] == "/admin/users/123"
        assert attrs["hx-target"] == Zones.DATA.selector
        assert "hx-swap" in attrs

    def test_for_delete_with_confirm(self):
        """for_delete with confirm should add hx-confirm."""
        attrs = HTMXAttrs.for_delete(
            "/admin/users/123",
            confirm_message="Delete this user?",
        )

        assert attrs["hx-confirm"] == "Delete this user?"

    def test_for_delete_custom_zone(self):
        """for_delete with custom zone should use that zone."""
        attrs = HTMXAttrs.for_delete(
            "/admin/users/123",
            target_zone=Zones.TABLE,
        )

        assert attrs["hx-target"] == Zones.TABLE.selector

    def test_for_bulk_action(self):
        """for_bulk_action should generate correct attrs."""
        attrs = HTMXAttrs.for_bulk_action("/admin/users/bulk/delete", "DELETE")

        assert attrs["hx-delete"] == "/admin/users/bulk/delete"
        assert attrs["hx-target"] == Zones.DATA.selector
        # Should include checked checkboxes
        assert "hx-include" in attrs
        assert "[name='ids']:checked" in attrs["hx-include"]
        assert "hx-params" not in attrs

    def test_for_bulk_action_with_confirm(self):
        """for_bulk_action with confirm should add hx-confirm."""
        attrs = HTMXAttrs.for_bulk_action(
            "/admin/users/bulk/delete",
            "DELETE",
            confirm_message="Delete all selected?",
        )

        assert attrs["hx-confirm"] == "Delete all selected?"

    def test_for_form_submit(self):
        """for_form_submit should generate correct attrs."""
        attrs = HTMXAttrs.for_form_submit("/admin/users", "POST")

        assert attrs["hx-post"] == "/admin/users"
        assert attrs["hx-target"] == Zones.DATA.selector

    def test_for_form_submit_custom_zone(self):
        """for_form_submit with custom zone should use that zone."""
        attrs = HTMXAttrs.for_form_submit(
            "/admin/users",
            "POST",
            target_zone=Zones.TABLE,
        )

        assert attrs["hx-target"] == Zones.TABLE.selector

    def test_merge(self):
        """merge should combine attribute dicts."""
        attrs1 = {"hx-get": "/url", "hx-target": "#a"}
        attrs2 = {"hx-target": "#b", "hx-swap": "innerHTML"}

        merged = HTMXAttrs.merge(attrs1, attrs2)

        assert merged["hx-get"] == "/url"
        assert merged["hx-target"] == "#b"  # Later overrides
        assert merged["hx-swap"] == "innerHTML"

    def test_for_live_table_input_targets_data_zone(self, full_state):
        """for_live_table_input should target DATA zone with hx-select."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")

        assert attrs["hx-target"] == Zones.DATA.selector
        assert attrs["hx-swap"] == "innerHTML"
        assert attrs["hx-select"] == Zones.DATA.selector

    def test_for_live_table_input_uses_hx_include(self, full_state):
        """for_live_table_input should include hidden state inputs + search input."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")

        assert "hx-include" in attrs
        assert Zones.DATA.selector in attrs["hx-include"]
        assert "data-state" in attrs["hx-include"]
        assert Zones.SEARCH.id in attrs["hx-include"]

    def test_for_live_table_input_base_url(self, full_state):
        """for_live_table_input should use unpaged base URL."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")

        assert attrs["hx-get"] == "/admin/users/"
        # Should NOT have page baked in since it resets
        assert "page=" not in attrs["hx-get"]

    def test_for_live_table_input_pushes_url(self, full_state):
        """for_live_table_input should push URL."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")
        assert attrs["hx-push-url"] == "true"

    def test_for_live_table_input_custom_input_name(self, full_state):
        """for_live_table_input should accept custom input name."""
        attrs = HTMXAttrs.for_live_table_input(
            full_state, "/admin/users", input_name="filter_q"
        )
        # The custom input name should be referenced in the include selector
        assert "filter_q" in attrs.get("hx-include", "")

    def test_for_live_table_input_documents_exception(self, full_state):
        """for_live_table_input docstring should explain the baked-URL exception."""
        doc = HTMXAttrs.for_live_table_input.__doc__
        assert doc is not None
        assert "exception" in doc.lower() or "live" in doc.lower()

    def test_for_live_table_input_with_full_state(self, full_state):
        """for_live_table_input should work with search, filters, sort."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")

        assert attrs["hx-get"] == "/admin/users/"
        assert attrs["hx-target"] == Zones.DATA.selector
        assert attrs["hx-params"] == "*"

    def test_for_live_table_input_custom_prefix_trailing_slash(self, full_state):
        """for_live_table_input should handle trailing-slash prefix."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users/")
        assert attrs["hx-get"] == "/admin/users/"

    def test_for_live_table_input_custom_prefix_no_slash(self, full_state):
        """for_live_table_input should handle prefix without trailing slash."""
        attrs = HTMXAttrs.for_live_table_input(full_state, "/admin/users")
        assert attrs["hx-get"] == "/admin/users/"

    def test_full_refresh_with_extra_params(self, state):
        """Extra params should be passed through."""
        attrs = HTMXAttrs.for_full_refresh(
            state,
            "/admin/users",
            custom_filter="active",
        )

        assert "custom_filter=active" in attrs["hx-get"]
