"""Unit tests for Phase 4 features: activity logging, inline edit, conditional fields."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# 4.1 Activity logging — ResourceController._emit_audit
# ---------------------------------------------------------------------------


class TestActivityLogging:
    def _make_controller(self):
        from lexigram.admin.controllers.resource import ResourceController, ResourceMeta

        class ConcreteController(ResourceController):
            meta = ResourceMeta(name="user", label="User", label_plural="Users")

            def get_data_source(self):
                return MagicMock()

            def render_list(self, *a, **kw):
                return ""

            def render_detail(self, *a, **kw):
                return ""

            def render_form(self, *a, **kw):
                return ""

        ctrl = ConcreteController()
        return ctrl

    @pytest.mark.asyncio
    async def test_emit_audit_does_nothing_without_logger(self) -> None:
        ctrl = self._make_controller()
        request = MagicMock()
        request.state.user = None
        request.client = None
        request.headers = {}
        request.url = "http://test/"
        # Should not raise
        await ctrl._emit_audit(request, "user.create", item_id="1")

    @pytest.mark.asyncio
    async def test_emit_audit_calls_logger_log(self) -> None:
        ctrl = self._make_controller()
        mock_logger = MagicMock()
        mock_logger.log = AsyncMock()
        ctrl.set_audit_logger(mock_logger)

        request = MagicMock()
        request.state.user = MagicMock()
        request.state.user.id = "user-42"
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        request.url = "http://test/admin/users/1"

        await ctrl._emit_audit(request, "user.create", item_id="1", new_values={"name": "Alice"})

        mock_logger.log.assert_awaited_once()
        entry = mock_logger.log.call_args[0][0]
        assert entry.action == "user.create"
        assert entry.actor_id == "user-42"
        assert entry.resource_id == "1"
        assert entry.resource_type == "user"
        assert entry.new_values == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_emit_audit_gracefully_handles_logger_failure(self) -> None:
        ctrl = self._make_controller()
        mock_logger = MagicMock()
        mock_logger.log = AsyncMock(side_effect=RuntimeError("db down"))
        ctrl.set_audit_logger(mock_logger)

        request = MagicMock()
        request.state.user = None
        request.client = None
        request.headers = {}
        request.url = "http://test/"
        # Must not propagate the error
        await ctrl._emit_audit(request, "user.delete", item_id="99")

    def test_set_audit_logger_assigns(self) -> None:
        ctrl = self._make_controller()
        mock_logger = MagicMock()
        ctrl.set_audit_logger(mock_logger)
        assert ctrl._audit_logger is mock_logger


# ---------------------------------------------------------------------------
# 4.3 Inline table editing — InlineEditCell component
# ---------------------------------------------------------------------------


class TestInlineEditCell:
    def test_renders_display_value(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(value="Alice", resource_url="/admin/users/1", field_name="name")
        html = str(cell.render())
        assert "Alice" in html

    def test_renders_htmx_patch_attribute(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(value="Alice", resource_url="/admin/users/1", field_name="name")
        html = str(cell.render())
        assert "hx-patch" in html
        assert "/admin/users/1" in html

    def test_renders_field_name_in_input(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(value="42", resource_url="/admin/users/42", field_name="age", cell_type="number")
        html = str(cell.render())
        assert 'name="age"' in html

    def test_non_editable_renders_plain_text(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(value="Alice", resource_url="/admin/users/1", field_name="name", editable=False)
        html = str(cell.render())
        assert "Alice" in html
        assert "hx-patch" not in html
        assert "<input" not in html

    def test_renders_select_with_options(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(
            value="active",
            resource_url="/admin/users/1",
            field_name="status",
            cell_type="select",
            options=[{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}],
        )
        html = str(cell.render())
        assert "<select" in html
        assert "Active" in html
        assert "Inactive" in html

    def test_renders_textarea_for_textarea_type(self) -> None:
        from lexigram.admin.ui.molecules.inline_edit_cell import InlineEditCell

        cell = InlineEditCell(value="Long text", resource_url="/admin/posts/1", field_name="body", cell_type="textarea")
        html = str(cell.render())
        assert "<textarea" in html


# ---------------------------------------------------------------------------
# 4.6 Conditional form fields — LayoutNode.visible_when + Field.visible_when
# ---------------------------------------------------------------------------


class TestConditionalFormFields:
    def test_field_node_wraps_with_x_show(self) -> None:
        from unittest.mock import MagicMock

        from lexigram.admin.forms.layout import FieldNode

        mock_form = MagicMock()
        mock_field = MagicMock()
        mock_field.render.return_value = "<input />"
        mock_form.fields = {"price": mock_field}

        node = FieldNode(field_name="price", visible_when="formData.show_price")
        html = str(node.render(mock_form))
        assert "x-show" in html
        assert "formData.show_price" in html

    def test_field_node_no_wrapper_when_no_condition(self) -> None:
        from unittest.mock import MagicMock

        from lexigram.admin.forms.layout import FieldNode

        mock_form = MagicMock()
        mock_field = MagicMock()
        mock_field.render.return_value = "<input />"
        mock_form.fields = {"name": mock_field}

        node = FieldNode(field_name="name")
        result = node.render(mock_form)
        # No x-show wrapper — result is the raw field render
        assert result == "<input />"

    def test_section_wraps_with_x_show(self) -> None:
        from lexigram.admin.forms.layout import Section

        section = Section(title="Shipping", visible_when="formData.needs_shipping")
        mock_form = MagicMock()
        mock_form.fields = {}
        html = str(section.render(mock_form))
        assert "x-show" in html
        assert "formData.needs_shipping" in html

    def test_field_visible_when_stores_expression(self) -> None:
        from lexigram.admin.forms.fields import TextField

        field = TextField(label="Price")
        result = field.visible_when("formData.type === 'paid'")
        assert result is field  # fluent API returns self
        assert field._visible_expression == "formData.type === 'paid'"

    def test_render_with_conditional_wraps_when_expression_set(self) -> None:
        from lexigram.admin.forms.fields import TextField

        field = TextField(label="VAT", name="vat_number")
        field.visible_when("formData.show_vat")
        html = str(field.render_with_conditional())
        assert "x-show" in html
        assert "formData.show_vat" in html

    def test_render_with_conditional_no_wrapper_when_no_expression(self) -> None:
        from lexigram.admin.forms.fields import TextField

        field = TextField(label="Name", name="name")
        result = field.render_with_conditional()
        # Should just return the normal render output
        rendered_str = str(result)
        assert "x-show" not in rendered_str
