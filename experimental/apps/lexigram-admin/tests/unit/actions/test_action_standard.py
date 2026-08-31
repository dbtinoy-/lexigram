from __future__ import annotations

from lexigram.admin.actions.standard import (
    CloneAction,
    CreateAction,
    DeleteAction,
    DeleteBulkAction,
    EditAction,
    ExportAction,
    ExportBulkAction,
    PurgeAction,
    RestoreAction,
    ViewAction,
)
from lexigram.admin.actions.types import ActionContext


class TestEditAction:
    def test_edit_url(self) -> None:
        action = EditAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42/edit" in result
        assert "hx-get" in result
        assert "Edit" in result

    def test_edit_no_id_returns_empty(self) -> None:
        action = EditAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({}, ctx)
        assert result == ""

    def test_edit_none_record_returns_empty(self) -> None:
        action = EditAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert result == ""


class TestViewAction:
    def test_view_url(self) -> None:
        action = ViewAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42" in result
        assert "hx-get" in result


class TestDeleteAction:
    def test_delete_url(self) -> None:
        action = DeleteAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42" in result

    def test_delete_uses_hx_get(self) -> None:
        action = DeleteAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "1"}, ctx)
        assert "hx-get" in result
        assert "/users/1/delete-confirm" in result


class TestCreateAction:
    def test_create_url(self) -> None:
        action = CreateAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert "/users/create" in result
        assert "hx-get" in result
        assert "Create" in result


class TestCloneAction:
    def test_clone_url(self) -> None:
        action = CloneAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/clone" in result


class TestRestoreAction:
    def test_restore_url(self) -> None:
        action = RestoreAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/restore" in result


class TestPurgeAction:
    def test_purge_url(self) -> None:
        action = PurgeAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/purge" in result

    def test_purge_uses_hx_delete(self) -> None:
        action = PurgeAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "1"}, ctx)
        assert "hx-delete" in result
        assert "hx-confirm" in result


class TestDeleteBulkAction:
    def test_bulk_delete_url(self) -> None:
        action = DeleteBulkAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button([{"id": "1"}, {"id": "2"}], ctx)
        assert "/users/bulk-delete-confirm" in result
        assert "hx-get" in result
        assert "hx-target" in result
        assert "#slide-over-container" in result
        assert "hx-include" in result
        assert "lexigram-table" in result


class TestExportAction:
    def test_export_url(self) -> None:
        action = ExportAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42/export" in result
        assert "hx-get" in result
        assert "Export" in result

    def test_export_defaults(self) -> None:
        action = ExportAction()
        assert action.name == "export"
        assert action.label == "Export"
        assert action.icon == "download"

    def test_export_custom_label(self) -> None:
        action = ExportAction(label="Download CSV")
        assert action.label == "Download CSV"

    def test_export_no_id_returns_empty(self) -> None:
        action = ExportAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({}, ctx)
        assert result == ""


class TestExportBulkAction:
    def test_bulk_export_uses_native_download_metadata(self) -> None:
        action = ExportBulkAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button([{"id": "1"}, {"id": "2"}], ctx)
        assert 'data-bulk-download-url="/users/bulk"' in result
        assert 'data-bulk-action="export"' in result
        assert "LexigramDownloadBulk" in result
        assert "hx-post" not in result

    def test_bulk_export_defaults(self) -> None:
        action = ExportBulkAction()
        assert action.name == "export"
        assert action.label == "Export Selected"
        assert action.icon == "download"

    def test_bulk_export_custom_label(self) -> None:
        action = ExportBulkAction(label="Export All")
        assert action.label == "Export All"

    def test_bulk_export_no_records_still_renders_deferred_download(self) -> None:
        action = ExportBulkAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button([], ctx)
        assert 'data-bulk-download-url="/users/bulk"' in result
