"""Tests for CalendarView, KanbanView, and TreeView."""

from __future__ import annotations

from datetime import date

import pytest

from lexigram.admin.views import CalendarView, KanbanView, TreeView


# ---------------------------------------------------------------------------
# CalendarView
# ---------------------------------------------------------------------------

class TestCalendarView:
    def _records(self):
        return [
            {"id": "1", "name": "Event A", "created_at": "2024-03-05"},
            {"id": "2", "name": "Event B", "created_at": "2024-03-05"},
            {"id": "3", "name": "Event C", "created_at": "2024-03-15"},
            {"id": "4", "name": "Other Month", "created_at": "2024-04-01"},
        ]

    def test_render_returns_html(self) -> None:
        view = CalendarView(month=3, year=2024)
        html = view.render(self._records())
        assert "<table" in html
        assert "March 2024" in html

    def test_render_includes_event_names(self) -> None:
        view = CalendarView(month=3, year=2024)
        html = view.render(self._records())
        assert "Event A" in html
        assert "Event B" in html
        assert "Event C" in html

    def test_other_month_excluded(self) -> None:
        view = CalendarView(month=3, year=2024)
        html = view.render(self._records())
        assert "Other Month" not in html

    def test_group_by_day(self) -> None:
        view = CalendarView(month=3, year=2024)
        grouped = view.group_by_day(self._records())
        assert len(grouped[5]) == 2
        assert len(grouped[15]) == 1

    def test_render_empty_records(self) -> None:
        view = CalendarView(month=1, year=2024)
        html = view.render([])
        assert "January 2024" in html
        assert "<table" in html

    def test_custom_date_field(self) -> None:
        records = [{"id": "1", "name": "X", "event_date": "2024-06-10"}]
        view = CalendarView(date_field="event_date", title_field="name", month=6, year=2024)
        html = view.render(records)
        assert "X" in html

    def test_view_type(self) -> None:
        view = CalendarView()
        assert view.view_type == "calendar"

    def test_day_headers_present(self) -> None:
        view = CalendarView(month=3, year=2024)
        html = view.render([])
        assert "Mon" in html
        assert "Sun" in html

    def test_datetime_string_parsed(self) -> None:
        records = [{"id": "1", "name": "Y", "created_at": "2024-03-20T10:30:00"}]
        view = CalendarView(month=3, year=2024)
        grouped = view.group_by_day(records)
        assert 20 in grouped


# ---------------------------------------------------------------------------
# KanbanView
# ---------------------------------------------------------------------------

class TestKanbanView:
    def _records(self):
        return [
            {"id": "1", "name": "Task A", "status": "todo"},
            {"id": "2", "name": "Task B", "status": "in_progress"},
            {"id": "3", "name": "Task C", "status": "done"},
            {"id": "4", "name": "Task D", "status": "done"},
            {"id": "5", "name": "Task E", "status": "unknown"},
        ]

    def test_render_returns_html(self) -> None:
        view = KanbanView()
        html = view.render(self._records())
        assert "kanban" in html

    def test_columns_rendered(self) -> None:
        view = KanbanView()
        html = view.render(self._records())
        assert 'data-status="todo"' in html
        assert 'data-status="in_progress"' in html
        assert 'data-status="done"' in html

    def test_cards_in_correct_columns(self) -> None:
        view = KanbanView()
        html = view.render(self._records())
        assert "Task A" in html
        assert "Task B" in html
        assert "Task C" in html

    def test_group_by_status(self) -> None:
        view = KanbanView()
        grouped = view.group_by_status(self._records())
        assert len(grouped["todo"]) == 1
        assert len(grouped["done"]) == 2
        assert len(grouped["_other"]) == 1

    def test_custom_columns(self) -> None:
        view = KanbanView(columns=["open", "closed"], status_field="state")
        records = [
            {"id": "1", "name": "A", "state": "open"},
            {"id": "2", "name": "B", "state": "closed"},
        ]
        grouped = view.group_by_status(records)
        assert len(grouped["open"]) == 1
        assert len(grouped["closed"]) == 1

    def test_view_type(self) -> None:
        view = KanbanView()
        assert view.view_type == "kanban"

    def test_count_shown_in_header(self) -> None:
        view = KanbanView()
        html = view.render(self._records())
        assert 'class="kanban-count"' in html

    def test_subtitle_field(self) -> None:
        view = KanbanView(subtitle_field="description")
        records = [{"id": "1", "name": "A", "status": "todo", "description": "Do this"}]
        html = view.render(records)
        assert "Do this" in html


# ---------------------------------------------------------------------------
# TreeView
# ---------------------------------------------------------------------------

class TestTreeView:
    def _flat_records(self):
        return [
            {"id": "root1", "name": "Root 1", "parent_id": None},
            {"id": "root2", "name": "Root 2", "parent_id": None},
            {"id": "child1", "name": "Child 1", "parent_id": "root1"},
            {"id": "child2", "name": "Child 2", "parent_id": "root1"},
            {"id": "grandchild1", "name": "Grandchild 1", "parent_id": "child1"},
        ]

    def test_render_returns_html(self) -> None:
        view = TreeView()
        html = view.render(self._flat_records())
        assert "<ul" in html
        assert "tree" in html

    def test_root_nodes_rendered(self) -> None:
        view = TreeView()
        html = view.render(self._flat_records())
        assert "Root 1" in html
        assert "Root 2" in html

    def test_children_rendered(self) -> None:
        view = TreeView()
        html = view.render(self._flat_records())
        assert "Child 1" in html
        assert "Child 2" in html
        assert "Grandchild 1" in html

    def test_build_tree_structure(self) -> None:
        view = TreeView()
        tree = view.build_tree(self._flat_records())
        assert len(tree[None]) == 2  # 2 root nodes
        assert len(tree["root1"]) == 2  # root1 has 2 children
        assert len(tree["child1"]) == 1  # child1 has 1 child

    def test_empty_records(self) -> None:
        view = TreeView()
        html = view.render([])
        assert "<ul" in html

    def test_view_type(self) -> None:
        view = TreeView()
        assert view.view_type == "tree"

    def test_custom_fields(self) -> None:
        view = TreeView(id_field="pk", parent_field="parent_pk", label_field="title")
        records = [
            {"pk": "1", "title": "Root", "parent_pk": None},
            {"pk": "2", "title": "Child", "parent_pk": "1"},
        ]
        html = view.render(records)
        assert "Root" in html
        assert "Child" in html

    def test_data_id_attributes(self) -> None:
        view = TreeView()
        html = view.render(self._flat_records())
        assert 'data-id="root1"' in html
        assert 'data-id="child1"' in html

    def test_depth_attribute(self) -> None:
        view = TreeView()
        html = view.render(self._flat_records())
        assert 'data-depth="0"' in html
        assert 'data-depth="1"' in html
        assert 'data-depth="2"' in html
