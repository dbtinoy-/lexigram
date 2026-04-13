from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.config import TableConfiguration
from lexigram.admin.resources.base import Resource
from lexigram.admin.ui.organisms.data_table import DataTable


def test_data_table_renders_grouped_rows():
    data = [
        {"id": 1, "name": "Alice", "role": "Admin"},
        {"id": 2, "name": "Bob", "role": "User"},
        {"id": 3, "name": "Charlie", "role": "Admin"},
    ]

    config = TableConfiguration(
        columns=[TextColumn("name"), TextColumn("role")], group_by="role",
    )

    dt = DataTable(config=config, data=data, resource_prefix="/admin/users")

    html = render_to_string(dt)

    # Check for group headers
    assert "Admin" in html
    assert "User" in html
    assert "(2)" in html  # Admin count
    assert "(1)" in html  # User count

    # Check for interactions (handling HTML escaping for single quotes)
    # The attributes might be escaped like toggleGroup(&#x27;Admin&#x27;)
    assert "toggleGroup" in html
    assert "Admin" in html

    # Check for row visibility logic - searching for the substring pattern
    # We look for x-show="!collapsedGroups.includes('Admin')" which handles escaping
    # We'll check for partial string since escaping might vary
    assert "!collapsedGroups.includes" in html


def test_group_by_handles_missing_keys():
    data = [
        {"id": 1, "name": "Alice", "role": "Admin"},
        {"id": 2, "name": "Bob"},  # Missing role
    ]

    config = TableConfiguration(
        columns=[TextColumn("name"), TextColumn("role")], group_by="role",
    )

    dt = DataTable(config=config, data=data, resource_prefix="/admin/users")

    html = render_to_string(dt)

    # Check for "Unknown" group
    assert "Unknown" in html
    assert "(1)" in html


def test_resource_group_by_class_attr_flows_through_config():
    class OrderResource(Resource):
        group_by = "status"

    assert OrderResource.get_table_config().group_by == "status"


def test_renders_group_by_switcher_in_toolbar():
    data = [
        {"id": 1, "name": "Alice", "role": "Admin"},
        {"id": 2, "name": "Bob", "role": "User"},
    ]

    config = TableConfiguration(
        columns=[TextColumn("name"), TextColumn("role")],
        group_by="role",
        resource_prefix="/admin/users",
    )

    dt = DataTable(config=config, data=data, resource_prefix="/admin/users")
    html = render_to_string(dt)

    assert "Group by" in html
    # Column options appear in the grouping dropdown
    assert "Role" in html
    assert "No grouping" in html
    # Current group is surfaced in the trigger label
    assert "Group by: Role" in html
    # HTMX navigation to the resource with group_by param
    assert "group_by=" in html
