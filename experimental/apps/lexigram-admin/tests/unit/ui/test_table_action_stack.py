from types import SimpleNamespace

from lexigram.admin.actions.standard import DeleteBulkAction
from lexigram.admin.ui.organisms.table.views.stacked import StackedView
from lexigram.admin.ui.organisms.table.views.tabular import TabularView
from lexigram.ui.actions.standard import EditAction


def make_config(actions=None, columns=None):
    return SimpleNamespace(
        actions=actions or [],
        columns=columns or [],
        resource_prefix="/admin",
        bulk_actions=None,
        expandable_relationship=False,
        group_by=None,
        reorderable_columns=False,
    )


class State:
    def __init__(self):
        self.column_order = []
        self.sort_by = None
        self.sort_order = "asc"


def test_tabular_actions_default_horizontal():
    config = make_config(actions=[EditAction()])
    state = State()
    view = TabularView(data=[{"id": "1"}], config=config, state=state)

    html = str(view.render())

    # By default, actions should be horizontal
    assert "flex items-center" in html
    assert "justify-end" in html


def test_tabular_actions_stack_when_configured():
    config = make_config(actions=[EditAction()])
    config.action_layout = "stack"
    state = State()
    view = TabularView(data=[{"id": "1"}], config=config, state=state)

    html = str(view.render())

    # The actions container should use vertical stacking classes when configured
    assert "flex flex-col" in html
    assert "items-end" in html


def test_stacked_view_actions_stack_vertically():
    config = make_config(actions=[EditAction()])
    state = State()
    view = StackedView(data=[{"id": "1", "name": "Test"}], config=config, state=state)

    html = str(view.render())

    # The card header action container should use vertical stacking classes
    assert "flex flex-col" in html
    assert "items-start" in html


def test_idless_stacked_rows_do_not_render_selection_or_actions():
    config = make_config(actions=[EditAction()])
    config.bulk_actions = [DeleteBulkAction()]
    state = State()
    view = StackedView(data=[{"name": "Unaddressable"}], config=config, state=state)

    html = str(view.render())

    assert 'name="ids"' not in html
    assert "edit" not in html.lower()
