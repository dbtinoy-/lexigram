"""
Comprehensive tests for RowActionManager and HeaderActionManager.

Tests:
- Row action registration and execution
- Standard row actions (View, Edit, Delete, Duplicate)
- Custom row actions
- Action groups
- Header action registration and execution
- Standard header actions (Create, Import, Export, Refresh)
- Column visibility management
- Table density control
- Keyboard shortcuts

Author: Lexigram Admin Team
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from lexigram.admin.actions.row_manager import (
    ActionGroup,
    ActionPosition,
    ActionStyle,
    IRowDataSource,
    RowAction,
    RowActionManager,
    row_action,
)


# -----------------------------------------------------------------------------
# Mock Data Sources
# -----------------------------------------------------------------------------


@dataclass
class MockRecord:
    id: int
    name: str
    status: str


class MockRowDataSource:
    """Mock data source for row operations."""

    def __init__(self):
        self.records = {
            1: MockRecord(1, "Item 1", "active"),
            2: MockRecord(2, "Item 2", "inactive"),
            3: MockRecord(3, "Item 3", "active"),
        }
        self.deleted_ids = []

    async def get_by_id(self, record_id: int) -> Optional[MockRecord]:
        return self.records.get(record_id)

    async def delete(self, record_id: int) -> bool:
        if record_id in self.records:
            del self.records[record_id]
            self.deleted_ids.append(record_id)
            return True
        return False

    async def duplicate(self, record_id: int) -> Optional[MockRecord]:
        original = self.records.get(record_id)
        if original:
            new_id = max(self.records.keys()) + 1
            duplicate = MockRecord(new_id, f"{original.name} (Copy)", original.status)
            self.records[new_id] = duplicate
            return duplicate
        return None


# -----------------------------------------------------------------------------
# Tests: Row Actions
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_row_action_registration():
    """Test registering row actions."""
    manager = RowActionManager()

    action = RowAction(
        name="test",
        label="Test Action",
        icon="test",
    )

    manager.add_action(action)

    assert manager.get_action("test") is not None
    assert manager.get_action("test").label == "Test Action"


@pytest.mark.asyncio
async def test_add_view_action():
    """Test adding standard View action."""
    manager = RowActionManager()
    manager.add_view_action(url_template="/view/{id}")

    action = manager.get_action("view")
    assert action is not None
    assert action.label == "View"
    assert action.icon == "eye"
    assert action.keyboard_shortcut == "v"


@pytest.mark.asyncio
async def test_add_edit_action():
    """Test adding standard Edit action."""
    manager = RowActionManager()
    manager.add_edit_action(url_template="/edit/{id}")

    action = manager.get_action("edit")
    assert action is not None
    assert action.label == "Edit"
    assert action.icon == "pencil"
    assert action.keyboard_shortcut == "e"


@pytest.mark.asyncio
async def test_add_delete_action():
    """Test adding standard Delete action."""
    data_source = MockRowDataSource()
    manager = RowActionManager(data_source)
    # Clear default actions and add delete action
    manager.clear_all_actions()
    manager.add_delete_action()

    action = manager.get_action("delete")
    assert action is not None
    assert action.label == "Delete"
    assert action.confirm is True
    assert action.handler is not None

    # Test execution
    result = await manager.execute_action("delete", 1)
    assert result is True
    assert 1 in data_source.deleted_ids


@pytest.mark.asyncio
async def test_add_duplicate_action():
    """Test adding standard Duplicate action."""
    data_source = MockRowDataSource()
    manager = RowActionManager(data_source)
    # Clear default actions and add duplicate action
    manager.clear_all_actions()
    manager.add_duplicate_action()

    action = manager.get_action("duplicate")
    assert action is not None
    assert action.label == "Duplicate"

    # Test execution
    duplicate = await manager.execute_action("duplicate", 1)
    assert duplicate is not None
    assert duplicate.name == "Item 1 (Copy)"


@pytest.mark.asyncio
async def test_custom_row_action():
    """Test adding custom row action."""
    executed = []

    async def custom_handler(record_id):
        executed.append(record_id)
        return f"Processed {record_id}"

    manager = RowActionManager()
    manager.add_custom_action(
        name="process",
        label="Process",
        handler=custom_handler,
        icon="cog",
    )

    action = manager.get_action("process")
    assert action is not None
    assert action.label == "Process"

    result = await manager.execute_action("process", 42)
    assert result == "Processed 42"
    assert 42 in executed


@pytest.mark.asyncio
async def test_action_groups():
    """Test creating action groups."""
    manager = RowActionManager()

    action1 = RowAction(name="export_csv", label="Export CSV", icon="download")
    action2 = RowAction(name="export_json", label="Export JSON", icon="download")

    manager.create_action_group(
        name="export",
        label="Export",
        actions=[action1, action2],
        icon="file",
    )

    record = MockRecord(1, "Test", "active")
    groups = manager.get_visible_groups(record)

    assert len(groups) == 1
    assert groups[0].name == "export"
    assert len(groups[0].actions) == 2


@pytest.mark.asyncio
async def test_action_visibility():
    """Test action visibility based on record state."""
    manager = RowActionManager()
    # Clear default actions
    manager.clear_all_actions()

    # Action only visible for active records
    action = RowAction(
        name="activate",
        label="Activate",
        visible=lambda r: r.status == "inactive",
    )
    manager.add_action(action)

    active_record = MockRecord(1, "Active", "active")
    inactive_record = MockRecord(2, "Inactive", "inactive")

    assert len(manager.get_visible_actions(active_record)) == 0
    assert len(manager.get_visible_actions(inactive_record)) == 1


@pytest.mark.asyncio
async def test_action_positions():
    """Test action positioning."""
    manager = RowActionManager()
    manager.clear_all_actions()  # Clear default actions

    manager.add_action(
        RowAction(name="start1", label="Start 1", position=ActionPosition.ROW_START),
    )
    manager.add_action(
        RowAction(name="end1", label="End 1", position=ActionPosition.ROW_END),
    )
    manager.add_action(
        RowAction(
            name="dropdown1", label="Dropdown 1", position=ActionPosition.DROPDOWN,
        ),
    )

    record = MockRecord(1, "Test", "active")

    start_actions = manager.get_visible_actions(record, ActionPosition.ROW_START)
    end_actions = manager.get_visible_actions(record, ActionPosition.ROW_END)
    dropdown_actions = manager.get_visible_actions(record, ActionPosition.DROPDOWN)

    assert len(start_actions) == 1
    assert len(end_actions) == 1
    assert len(dropdown_actions) == 1


@pytest.mark.asyncio
async def test_keyboard_shortcuts():
    """Test keyboard shortcut handling."""
    manager = RowActionManager()

    manager.add_view_action(keyboard_shortcut="v")
    manager.add_edit_action(keyboard_shortcut="e")
    manager.add_delete_action(keyboard_shortcut="Delete")

    record = MockRecord(1, "Test", "active")

    # Test valid shortcut
    action = manager.handle_keyboard_shortcut("v", 1, record)
    assert action is not None
    assert action.name == "view"

    # Test invalid shortcut
    action = manager.handle_keyboard_shortcut("z", 1, record)
    assert action is None

    # Get all shortcuts
    shortcuts = manager.get_keyboard_shortcuts()
    assert "v" in shortcuts
    assert "e" in shortcuts
    assert "Delete" in shortcuts


@pytest.mark.asyncio
async def test_row_action_decorator():
    """Test @row_action decorator."""

    @row_action("email", "Send Email", icon="mail", keyboard_shortcut="m")
    async def send_email(record_id):
        return f"Email sent to {record_id}"

    assert hasattr(send_email, "_row_action_meta")
    meta = send_email._row_action_meta
    assert meta["name"] == "email"
