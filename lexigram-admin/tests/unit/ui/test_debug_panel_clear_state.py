from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.debug import StateDebugPanel


class MockSession:
    """Mock session for testing StateDebugPanel."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def is_empty(self) -> bool:
        return len(self._data) == 0

    def items(self):
        return list(self._data.items())


def test_debug_panel_renders_session_data():
    """Test that debug panel renders session data correctly."""
    session = MockSession({"foo": "bar"})
    html = render_to_string(StateDebugPanel(session=session))

    # Should display the session key/value
    assert "foo" in html
    assert "bar" in html
