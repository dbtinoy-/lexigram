from types import SimpleNamespace
from lexigram.ui.state import TableState

def make_req(query_params):
    return SimpleNamespace(query_params=query_params)

def test_legacy_layout_mapped_to_stack(capsys):
    req = make_req({"layout_type": "centered"})
    state = TableState.from_request(req)
    assert state.layout == "stack"

def test_invalid_view_falls_back_to_default():
    req = make_req({"data_view": "unknown_view"})
    state = TableState.from_request(req, defaults={"view": "tabular"})
    assert state.view == "tabular"
