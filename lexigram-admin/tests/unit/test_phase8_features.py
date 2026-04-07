"""Tests for Phase 8 features:
- JsonField (JSON field editing)
- SortableRecordList (drag-n-drop record reorder)
- ResourceLens / LensRegistry (alternative query views)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# JsonField
# ---------------------------------------------------------------------------

from lexigram.admin.forms.fields import FieldType, JsonField


class TestJsonField:
    def test_field_type_json_exists(self) -> None:
        assert FieldType.JSON == "json"

    def test_bind_dict_value(self) -> None:
        f = JsonField(label="Config").bind({"key": "value", "count": 42})
        assert '"key"' in f.value
        assert '"value"' in f.value

    def test_bind_list_value(self) -> None:
        f = JsonField(label="Tags").bind([1, 2, 3])
        assert "[" in f.value

    def test_bind_json_string(self) -> None:
        f = JsonField().bind('{"a": 1}')
        assert '"a"' in f.value

    def test_bind_invalid_json_string_stored_as_raw(self) -> None:
        f = JsonField().bind("not valid json")
        assert f.value == "not valid json"

    def test_bind_none_gives_empty(self) -> None:
        f = JsonField().bind(None)
        assert f.value == ""

    def test_parse_value_valid(self) -> None:
        f = JsonField()
        result = f.parse_value('{"x": 1}')
        assert result == {"x": 1}

    def test_parse_value_invalid_raises(self) -> None:
        f = JsonField()
        with pytest.raises(ValueError, match="Invalid JSON"):
            f.parse_value("not json")

    def test_render_has_textarea(self) -> None:
        f = JsonField(label="Config").bind({"k": "v"})
        html = str(f.render())
        assert "textarea" in html

    def test_render_contains_value(self) -> None:
        f = JsonField(label="Config").bind({"hello": "world"})
        html = str(f.render())
        assert "hello" in html

    def test_render_has_label(self) -> None:
        f = JsonField(label="My JSON")
        html = str(f.render())
        assert "My JSON" in html

    def test_render_has_monospace_class(self) -> None:
        f = JsonField()
        html = str(f.render())
        assert "font-mono" in html

    def test_custom_rows(self) -> None:
        f = JsonField(rows=20)
        html = str(f.render())
        assert "20" in html

    def test_disabled_renders_attribute(self) -> None:
        f = JsonField(disabled=True)
        html = str(f.render())
        assert "disabled" in html

    def test_help_text_rendered(self) -> None:
        f = JsonField(help_text="Enter valid JSON")
        html = str(f.render())
        assert "Enter valid JSON" in html

    def test_error_rendered(self) -> None:
        f = JsonField()
        f.errors = ["Invalid JSON syntax"]
        html = str(f.render())
        assert "Invalid JSON syntax" in html

    def test_indent_default_is_2(self) -> None:
        f = JsonField()
        assert f.indent == 2

    def test_custom_indent(self) -> None:
        # indent parameter stored correctly (used as visual hint)
        f = JsonField(indent=4)
        assert f.indent == 4


# ---------------------------------------------------------------------------
# SortableRecordList
# ---------------------------------------------------------------------------

from lexigram.admin.ui.organisms.sortable_list import SortableRecordList


class TestSortableRecordList:
    def test_renders_list_items(self) -> None:
        rows = [{"id": 1, "title": "Alpha"}, {"id": 2, "title": "Beta"}]
        w = SortableRecordList(rows=rows, reorder_url="/admin/posts/reorder")
        html = str(w.render())
        assert "Alpha" in html
        assert "Beta" in html

    def test_renders_data_id_attributes(self) -> None:
        rows = [{"id": 10, "title": "A"}, {"id": 20, "title": "B"}]
        w = SortableRecordList(rows=rows)
        html = str(w.render())
        assert 'data-id="10"' in html
        assert 'data-id="20"' in html

    def test_empty_list_shows_empty_label(self) -> None:
        w = SortableRecordList(rows=[], empty_label="Nothing here")
        html = str(w.render())
        assert "Nothing here" in html

    def test_default_empty_label(self) -> None:
        w = SortableRecordList(rows=[])
        html = str(w.render())
        assert "No records" in html

    def test_reorder_url_in_script(self) -> None:
        rows = [{"id": 1, "title": "A"}]
        w = SortableRecordList(rows=rows, reorder_url="/admin/items/reorder")
        html = str(w.render())
        assert "/admin/items/reorder" in html

    def test_custom_id_field(self) -> None:
        rows = [{"pk": 99, "name": "Item"}]
        w = SortableRecordList(rows=rows, id_field="pk", label_field="name")
        html = str(w.render())
        assert 'data-id="99"' in html
        assert "Item" in html

    def test_object_rows_supported(self) -> None:
        row = MagicMock()
        row.id = 5
        row.title = "Mock item"
        w = SortableRecordList(rows=[row])
        html = str(w.render())
        assert "Mock item" in html

    def test_save_order_button_rendered(self) -> None:
        rows = [{"id": 1, "title": "A"}]
        w = SortableRecordList(rows=rows)
        html = str(w.render())
        assert "Save order" in html

    def test_alpine_x_data_attribute(self) -> None:
        rows = [{"id": 1, "title": "A"}]
        w = SortableRecordList(rows=rows)
        html = str(w.render())
        assert "sortableRecords" in html

    def test_sortable_js_initialisation(self) -> None:
        rows = [{"id": 1, "title": "A"}]
        w = SortableRecordList(rows=rows)
        html = str(w.render())
        assert "Sortable" in html

    def test_drag_handle_rendered(self) -> None:
        rows = [{"id": 1, "title": "A"}]
        w = SortableRecordList(rows=rows)
        html = str(w.render())
        # Braille dots drag handle icon
        assert "⠿" in html


# ---------------------------------------------------------------------------
# ResourceLens / LensRegistry
# ---------------------------------------------------------------------------

from lexigram.admin.resources.lenses import LensRegistry, ResourceLens


class ActiveLens(ResourceLens):
    name = "active"
    label = "Active Records"
    query_filters = {"is_active": True}


class ArchivedLens(ResourceLens):
    name = "archived"
    label = "Archived"
    query_filters = {"is_archived": True}
    default_sort = "-archived_at"


class TestResourceLens:
    def test_get_name_from_attribute(self) -> None:
        assert ActiveLens.get_name() == "active"

    def test_get_name_from_class_name(self) -> None:
        class MyCustomLens(ResourceLens):
            pass

        assert MyCustomLens.get_name() == "my_custom"

    def test_get_label(self) -> None:
        assert ActiveLens.get_label() == "Active Records"

    def test_get_label_fallback(self) -> None:
        class UnlabeledLens(ResourceLens):
            name = "unlabeled"

        assert UnlabeledLens.get_label() == "Unlabeled"

    def test_apply_to_queryset_calls_filter(self) -> None:
        qs = MagicMock()
        qs.filter.return_value = qs
        result = ActiveLens.apply_to_queryset(qs)
        qs.filter.assert_called_once_with(is_active=True)
        assert result is qs

    def test_apply_to_queryset_no_filters(self) -> None:
        qs = MagicMock()

        class NoFilterLens(ResourceLens):
            name = "bare"

        result = NoFilterLens.apply_to_queryset(qs)
        qs.filter.assert_not_called()
        assert result is qs

    def test_resolve_columns_with_override(self) -> None:
        col = MagicMock()
        ActiveLens.columns = [col]
        assert ActiveLens.resolve_columns([]) == [col]
        ActiveLens.columns = None  # cleanup

    def test_resolve_columns_inherits_parent(self) -> None:
        parent_cols = [MagicMock()]
        assert ActiveLens.resolve_columns(parent_cols) is parent_cols

    def test_resolve_sort_with_override(self) -> None:
        assert ArchivedLens.resolve_sort("created_at") == "-archived_at"

    def test_resolve_sort_inherits_parent(self) -> None:
        assert ActiveLens.resolve_sort("-created_at") == "-created_at"

    def test_resolve_page_size_override(self) -> None:
        class SmallLens(ResourceLens):
            name = "small"
            page_size = 5

        assert SmallLens.resolve_page_size(20) == 5

    def test_resolve_page_size_inherits(self) -> None:
        assert ActiveLens.resolve_page_size(20) == 20

    def test_to_dict(self) -> None:
        d = ActiveLens.to_dict()
        assert d["name"] == "active"
        assert d["label"] == "Active Records"
        assert "icon" in d
        assert "description" in d


class TestLensRegistry:
    def test_register_and_get(self) -> None:
        reg = LensRegistry()
        reg.register(ActiveLens)
        assert reg.get("active") is ActiveLens

    def test_get_missing_returns_none(self) -> None:
        reg = LensRegistry()
        assert reg.get("nope") is None

    def test_duplicate_name_raises(self) -> None:
        reg = LensRegistry([ActiveLens])
        with pytest.raises(ValueError, match="already registered"):
            reg.register(ActiveLens)

    def test_all_returns_all_lenses(self) -> None:
        reg = LensRegistry([ActiveLens, ArchivedLens])
        assert len(reg.all()) == 2

    def test_names(self) -> None:
        reg = LensRegistry([ActiveLens, ArchivedLens])
        assert "active" in reg.names()
        assert "archived" in reg.names()

    def test_to_list(self) -> None:
        reg = LensRegistry([ActiveLens, ArchivedLens])
        lst = reg.to_list()
        assert len(lst) == 2
        assert all("name" in item for item in lst)

    def test_init_with_lenses(self) -> None:
        reg = LensRegistry(lenses=[ActiveLens])
        assert reg.get("active") is ActiveLens

    def test_empty_registry(self) -> None:
        reg = LensRegistry()
        assert reg.all() == []
        assert reg.names() == []
