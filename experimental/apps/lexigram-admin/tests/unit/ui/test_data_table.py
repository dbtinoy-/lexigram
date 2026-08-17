from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.config import TableConfiguration
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.config import ResourceConfig
from lexigram.admin.ui.organisms.data_table import DataTable


def test_data_table_renders_empty_state_when_no_data():
    dt = DataTable(
        columns=[TextColumn("name")], data=[], resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    assert "No results found" in html
    assert "Try adjusting your filters" in html


def test_data_table_empty_state_overrides_honored():
    config = TableConfiguration(
        columns=[TextColumn("name")],
        empty_state_title="Nothing here yet",
        empty_state_message="Create your first record to get started.",
        empty_state_icon="🗂️",
    )
    dt = DataTable(columns=[TextColumn("name")], data=[], config=config)
    html = render_to_string(dt)
    assert "Nothing here yet" in html
    assert "Create your first record to get started." in html
    assert "🗂️" in html
    assert "No results found" not in html


def test_resource_empty_state_class_attrs_flow_through_config():
    class ProductResource(Resource):
        empty_state_title = "No products"
        empty_state_message = "Add your first product."
        empty_state_icon = "📦"

    config = ProductResource.get_table_config()
    assert config.empty_state_title == "No products"
    assert config.empty_state_message == "Add your first product."
    assert config.empty_state_icon == "📦"


def test_resource_header_actions_flow_through_config():
    from lexigram.admin.actions.standard import ImportAction

    class ProductResource(Resource):
        header_actions = [ImportAction()]

    config = ProductResource.get_table_config()
    assert config.header_actions == ProductResource.header_actions


def test_resource_config_fluent_empty_state_flow_through():
    class ProductResource(Resource):
        config = ResourceConfig.builder().empty_state(
            title="No products",
            message="Add your first product.",
            icon="📦",
        )

    config = ProductResource.get_table_config()
    assert config.empty_state_title == "No products"
    assert config.empty_state_message == "Add your first product."
    assert config.empty_state_icon == "📦"


def test_data_table_renders_header_with_search_and_create():
    dt = DataTable(
        columns=[TextColumn("name")], data=[], resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    # header should contain search input wrapper and Create button
    assert "Create New" in html
    # Search input should be present
    assert "<input" in html or "Search" in html
